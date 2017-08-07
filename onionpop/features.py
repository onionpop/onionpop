from onionpop.cumul import extract

CELL_TYPE_KEYS = ['CREATE', 'CREATED', 'CREATE2', 'CREATED2', 'CREATED_FAST', 'CREATE_FAST', 'DESTROY', 'RELAY', 'RELAY_EARLY', 'UNKNOWN']
CELL_COMMAND_KEYS = ['BEGIN', 'BEGIN_DIR', 'CONNECTED', 'DATA', 'END', 'DROP', 'SENDME', 'EXTEND', 'EXTENDED', 'EXTEND2', 'EXTENDED2', 'TRUNCATE', 'TRUNCATED', 'RESOLVE', 'RESOLVED', 'ESTABLISH_INTRO', 'ESTABLISH_RENDEZVOUS', 'INTRODUCE1', 'INTRODUCE2', 'RENDEZVOUS1', 'RENDEZVOUS2', 'INTRO_ESTABLISHED', 'RENDEZVOUS_ESTABLISHED', 'INTRODUCE_ACK', 'SIG_CIRCPURPCHANGED', 'SIG_NEWCIRC', 'SIG_NEWSTRM', 'UNKNOWN']

class Node(object):
    def __init__(self, nickname, ip_address, fingerprint, is_relay, is_exit, is_guard):
        self.nickname = nickname
        self.ip_address = ip_address
        self.fingerprint = fingerprint
        self.is_relay = is_relay
        self.is_exit = is_exit
        self.is_guard = is_guard

class Cell(object):
    def __init__(self, chan_id, circ_id, timestamp, cell_type, cell_command, is_sent, is_outbound):
        self.chan_id = chan_id
        self.circ_id = circ_id
        self.timestamp = timestamp # e.g., 1235.465052
        cell_type_upper = cell_type.upper()
        self.ctype = cell_type_upper if cell_type_upper in CELL_TYPE_KEYS else 'UNKNOWN'
        cell_command_upper = cell_command.upper()
        self.command = cell_command_upper if cell_command_upper in CELL_COMMAND_KEYS else "UNKNOWN"
        self.is_sent = is_sent
        self.is_outbound = is_outbound

class Circuit(object):
    def __init__(self, chan_id, circ_id, prev_node, next_node, cell_list=None):
        self.cells = cell_list if cell_list is not None else [] # chronologically-ordered list of cells
        self.chan_id = chan_id
        self.circ_id = circ_id
        self.prev_node = prev_node
        self.next_node = next_node

    def add_cell(self, cell):
        if cell is not None and cell.chan_id == self.chan_id and cell.circ_id == self.circ_id:
            self.cells.append(cell)

class Features(object):
    def __init__(self, circuit):
        self.circuit = circuit
        self.circuit_features = None

    def count_cells(self, key_list, types_filter=[], commands_filter=[], limit=None):
        # absolute count keys
        d = {'recv_in':0, 'sent_in':0, 'recv_out':0, 'sent_out':0,
             'total_in':0, 'total_out':0, 'total_recv':0, 'total_sent':0}
        # cell-specific counts
        for k in key_list:
            d[k] = 0

        iter_count = 0
        for cell in self.circuit.cells:
            iter_count += 1
            if limit is not None and iter_count > limit:
                break

            # first handle absolute counts
            if cell.is_sent:
                if cell.is_outbound:
                    # sent to the outbound side
                    d['sent_out'] += 1
                    d['total_sent'] += 1
                    d['total_out'] += 1
                else:
                    # sent to the inbound side
                    d['sent_in'] += 1
                    d['total_sent'] += 1
                    d['total_in'] += 1
            else:
                if cell.is_outbound:
                    # received from the inbound side
                    d['recv_in'] += 1
                    d['total_recv'] += 1
                    d['total_in'] += 1
                else:
                    # received from the outbound side
                    d['recv_out'] += 1
                    d['total_recv'] += 1
                    d['total_out'] += 1

            # now handle cell-specific counts
            if cell.ctype in types_filter and cell.command in commands_filter:
                k = "{}_{}".format(cell.ctype, cell.command)
                if k in d:
                    d[k] += 1

        if limit is None:
            return d
        else:
            d2 = {}
            for k in d:
                d2["{}_first_{}".format(k, limit)] = d[k]
            return d2

    def get_cell_sequence(self, max_cells=None):
        sequence = []
        for cell in self.circuit.cells:
            # webpage classifier was trained on only
            # client-side received and client-side sent cells
            if cell.is_outbound: # this cell was on the server side
                continue

            # the remaining cells were either received or sent on client side
            direction_code = 0
            if cell.is_sent:
                # sent toward the client
                direction_code = -1
            else:
                # received from the client, would be headed toward the server
                direction_code = 1

            sequence.append((cell.timestamp, direction_code))

            if max_cells is not None and len(sequence) >= max_cells:
                break

        return sequence

    def get_lifetime(self):
        if len(self.circuit.cells) > 1:
            return self.circuit.cells[-1].timestamp - self.circuit.cells[0].timestamp
        else:
            return 0

    def _extract_circuit_features(self):
        if not self.circuit:
            return None

        # if we have already computed the features, don't bother recomputing
        # we set self.circuit_features to None if recomputation is required
        if self.circuit_features is not None:
            return self.circuit_features

        c = self.circuit
        features = []

        features.append(1 if c.next_node and c.next_node.is_relay else 0)
        features.append(1 if c.next_node and c.next_node.is_guard else 0)
        features.append(1 if c.next_node and c.next_node.is_exit else 0)

        features.append(1 if c.prev_node and c.prev_node.is_relay else 0)
        features.append(1 if c.prev_node and c.prev_node.is_guard else 0)
        features.append(1 if c.prev_node and c.prev_node.is_exit else 0)

        cell_type_keys = ["CREATE", "CREATED", "CREATE2", "CREATED2", "RELAY", "RELAY_EARLY"]
        cell_command_keys = ["EXTEND", "EXTENDED", "EXTEND2", "EXTENDED2", "UNKNOWN"]
        combo_keys = ['CREATE_UNKNOWN', 'CREATED_UNKNOWN', 'CREATE2_UNKNOWN', 'CREATED2_UNKNOWN',
        'RELAY_EARLY_EXTEND', 'RELAY_EXTENDED', 'RELAY_EARLY_EXTEND2', 'RELAY_EXTENDED2',
        'RELAY_UNKNOWN', 'RELAY_EARLY_UNKNOWN']

        counts = self.count_cells(combo_keys,
            types_filter=cell_type_keys, commands_filter=cell_command_keys)

        for label in combo_keys:
            features.append(counts[label])

        features.append(counts['total_sent'])
        features.append(counts['total_recv'])
        features.append(counts['sent_out'])
        features.append(counts['sent_in'])
        features.append(counts['recv_out'])
        features.append(counts['recv_in'])

        self.circuit_features = features
        return self.circuit_features

    def extract_purpose_features(self):
        return self._extract_circuit_features()

    def extract_position_features(self):
        return self._extract_circuit_features()

    def extract_webfp_features(self):
        if not self.circuit:
            return None

        cells = self.get_cell_sequence()
        features = extract(cells)

        return features


test_node1 = Node('R1', '1.1.1.1', '0000', True, False, True)
test_node2 = Node('R2', '1.1.1.2', 'FFFF', False, False, True)
test_circuit = Circuit(0, 0, test_node1, test_node2)
test_circuit.add_cell(Cell(0, 0, 1, 'create', 'UNKNOWN', True, True))
test_circuit.add_cell(Cell(0, 0, 0, 'created', 'UNKNOWN', True, True))
test_circuit.add_cell(Cell(0, 0, 1, 'relay', 'UNKNOWN', True, True))
