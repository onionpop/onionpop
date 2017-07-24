
CELL_TYPE_KEYS = ['create', 'created', 'create2', 'created2', 'created_fast', 'create_fast', 'destroy', 'relay', 'relay_early', 'unknown']
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
    def __init__(self, chan_id, circ_id, timestamp, type, command, is_sent, is_outbound):
        self.chan_id = chan_id
        self.circ_id = circ_id
        self.timestamp = timestamp # e.g., 1235.465052
        self.type = type if type in CELL_TYPE_KEYS else 'unknown'
        self.command = command if command in CELL_COMMAND_KEYS else "UNKNOWN"
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

    def count_cell_types(self, types_list):
        d = {t:0 for t in types_list}
        for cell in self.circuit.cells:
            if cell.type in d:
                d[cell.type] += 1
        return d

    def count_cell_commands(self, cmds_list):
        d = {cmd:0 for cmd in cmds_list}
        for cell in self.circuit.cells:
            if cell.command in d:
                d[cell.command] += 1
        return d

    def count_cells_types_commands(self, key_list, types_filter=[], commands_filter=[]):
        d = {k:0 for k in key_list}

        for cell in self.circuit.cells:
            if cell.type not in types_filter or cell.command not in commands_filter:
                continue
            k = "{}_{}".format(cell.type, cell.command)
            if k in d:
                d[k] += 1

        return d

    def count_cells(self, limit=None):
        d = {'recv_in':0, 'sent_in':0, 'recv_out':0, 'sent_out':0,
             'total_in':0, 'total_out':0, 'total_recv':0, 'total_sent':0}

        iter_count = 0
        for cell in self.circuit.cells:
            iter_count += 1
            if limit is not None and iter_count > limit:
                break

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

        if limit is None:
            return d
        else:
            d2 = {}
            for k in d:
                d2["{}_first_{}".format(k, limit)] = d[k]
            return d2

    def get_cell_sequence(self):
        return [(cell.timestamp, 1 if cell.is_outbound else -1) for cell in self.circuit.cells]

    def get_initial_cell_sequence(self, num_cells):
        sequence = []
        count = 0
        for cell in self.circuit.cells:
            count += 1
            if count > num_cells:
                break
            if cell.is_outbound:
                sequence.append('+1') # outbound side
            else:
                sequence.append('-1') # inbound side
        return ''.join(sequence)

    def get_lifetime(self):
        if len(self.circuit.cells) > 1:
            return self.circuit.cells[-1].timestamp - self.circuit.cells[0].timestamp
        else:
            return 0

    def extract_purpose_features(self):
        if not self.circuit:
            return None

        c = self.circuit
        features = []

        features.append(1 if c.next_node and c.next_node.is_relay else 0)
        features.append(1 if c.next_node and c.next_node.is_guard else 0)
        features.append(1 if c.next_node and c.next_node.is_exit else 0)

        features.append(1 if c.prev_node and c.prev_node.is_relay else 0)
        features.append(1 if c.prev_node and c.prev_node.is_guard else 0)
        features.append(1 if c.prev_node and c.prev_node.is_exit else 0)

        cell_type_keys = ["create", "created", "create2", "created2", "relay", "relay_early"]
        cell_command_keys = ["EXTEND", "EXTENDED", "EXTEND2", "EXTENDED2"]
        combo_keys = ['create_UNKNOWN', 'created_UNKNOWN', 'create2_UNKNOWN', 'created2_UNKNOWN',
        'relay_early_EXTEND', 'relay_EXTENDED', 'relay_early_EXTEND2', 'relay_EXTENDED2',
        'relay_UNKNOWN', 'relay_early_UNKNOWN']

        cell_type_counts = self.count_cells_types_commands(combo_keys,
            types_filter=cell_type_keys, commands_filter=cell_command_keys)

        for label in combo_keys:
            features.append(cell_type_counts[label])

        counts = self.count_cells()
        features.append(counts['total_sent'])
        features.append(counts['total_recv'])
        features.append(counts['sent_out'])
        features.append(counts['sent_in'])
        features.append(counts['recv_out'])
        features.append(counts['recv_in'])

        return features

    def extract_position_features(self):
        return self.extract_purpose_features()

test_node1 = Node('R1', '1.1.1.1', '0000', True, False, True)
test_node2 = Node('R2', '1.1.1.2', 'FFFF', False, False, True)
test_circuit = Circuit(0, 0, test_node1, test_node2)
test_circuit.add_cell(Cell(0, 0, 0, 'create', 'UNKNOWN', True, True))
