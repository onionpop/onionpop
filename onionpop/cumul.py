#!/usr/bin/python

# Modified from Panchenko et al.'s original script.

# Script to generate Features from previously prepared data
# Outlier Removal should be done beforehand (!)

import numpy as np
from itertools import islice


def extract(instance, num_interpolation_points=100):
    features = []

    total = []
    cum = []
    pos = []
    neg = []
    inSize = 0
    outSize = 0
    inCount = 0
    outCount = 0

    # Process trace
    for _, packetsize in instance:
        #f2 = p.strip().split('\t')[1]
        #if f2 == 'None':
        #    continue
        #packetsize = int(f2)

        # incoming packets
        if packetsize > 0:
            inSize += packetsize
            inCount += 1

            # cumulated packetsizes
            if len(cum) == 0:
                cum.append(packetsize)
                total.append(packetsize)
                pos.append(packetsize)
                neg.append(0)
            else:
                cum.append(cum[-1] + packetsize)
                total.append(total[-1] + abs(packetsize))
                pos.append(pos[-1] + packetsize)
                neg.append(neg[-1] + 0)

        # outgoing packets
        if packetsize < 0:
            outSize += abs(packetsize)
            outCount += 1
            if len(cum) == 0:
                cum.append(packetsize)
                total.append(abs(packetsize))
                pos.append(0)
                neg.append(abs(packetsize))
            else:
                cum.append(cum[-1] + packetsize)
                total.append(total[-1] + abs(packetsize))
                pos.append(pos[-1] + 0)
                neg.append(neg[-1] + abs(packetsize))

    # add feature
    features.append(inCount)
    features.append(outCount)
    features.append(outSize)
    features.append(inSize)

    cumFeatures = np.interp(np.linspace(total[0], total[-1], num_interpolation_points + 1), total, cum)
    for el in islice(cumFeatures, 1, None):
        features.append(el)

    return features
