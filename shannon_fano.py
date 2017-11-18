"""Shannon Fano compression"""

from collections import Counter, defaultdict


BYTE_LENGTH = 8


def frequency(file_name):
    """Build characters frequency table"""
    counter = Counter()
    total = 0

    with open(file_name, 'r') as file_input:
        for char in iter(lambda: file_input.read(1), ''):
            counter.update(char)
            total += 1

    return total, [(char, stat/total) for char, stat in counter.most_common()]


def to_byte(data):
    """Encode given data as one byte"""
    return data.to_bytes(1, byteorder="big")


def from_byte(data):
    """Decode integer from one byte"""
    return int.from_bytes(data, byteorder="big")


def encode(frequency_data):
    """Build Shannon Fano encoder"""
    encoder = defaultdict(list)
    stack = [(0, len(frequency_data)-1)]

    while stack:
        start, end = stack.pop()

        if start == end:
            continue
        elif end - start == 1:
            start_char = frequency_data[start][0]
            encoder[start_char].append('0')

            end_char = frequency_data[end][0]
            encoder[end_char].append('1')
        else:
            half = 0

            for i in range(start, end+1):
                half += frequency_data[i][1]

            partition = 0
            partition_index = -1
            half *= 0.5

            for i in range(start, end+1):
                if partition <= half:
                    i_char = frequency_data[i][0]
                    encoder[i_char].append('0')
                else:
                    i_char = frequency_data[i][0]
                    encoder[i_char].append('1')
                    if partition_index < 0:
                        partition_index = i
                partition += frequency_data[i][1]

            stack.append((partition_index, end))
            stack.append((start, partition_index-1))

    for key, value in encoder.items():
        encoder[key] = ''.join(value)

    return encoder


def pack_metadata(file_output, encoder, input_size, frequency_data):
    """Write metadata into compressed file"""
    encoder_size = to_byte(len(frequency_data))

    file_output.write(encoder_size)
    file_output.write(to_byte(input_size))

    for key, value in encoder.items():
        encoded_key = to_byte(ord(key))
        encoded_value_len = to_byte(len(value))
        encoded_value = to_byte(int(value, 2))

        file_output.write(encoded_key)
        file_output.write(encoded_value_len)
        file_output.write(encoded_value)


def pack_data(file_input, file_output, encoder):
    """Write compressed data into file"""
    bits = ''

    with open(file_input, 'r') as fin:
        for char in iter(lambda: fin.read(1), ''):
            bits += encoder[char]
            while len(bits) > BYTE_LENGTH:
                bit_str = bits[:BYTE_LENGTH]
                bits = bits[BYTE_LENGTH:]
                byte = to_byte(int(bit_str, 2))
                file_output.write(byte)

    if bits:
        bits = bits.ljust(BYTE_LENGTH, '0')
        file_output.write(to_byte(int(bits, 2)))


def pack(finput, foutput):
    """Compress file"""
    input_size, frequency_data = frequency(finput)
    encoder = encode(frequency_data)
    with open(foutput, 'wb') as fout:
        pack_metadata(fout, encoder, input_size, frequency_data)
        pack_data(finput, fout, encoder)


def unpack_metadata(file_input):
    """Read metadata from compressed file"""
    decoder_size = 3 * from_byte(file_input.read(1))
    input_size = from_byte(file_input.read(1))
    decoder = {}
    val_lens = set()

    while decoder_size > 0:
        key = chr(from_byte(file_input.read(1)))
        val_len = from_byte(file_input.read(1))
        val_lens.add(val_len)
        val = bin(
            from_byte(file_input.read(1))
        )[2:].rjust(val_len, '0')
        decoder[val] = key
        decoder_size -= 3
    return input_size, decoder, val_lens


def unpack_data(file_input, file_output, input_size, decoder, val_lens):
    """Decompress data"""
    byte = file_input.read(1)
    bits = []

    while byte:
        byte = ord(byte)
        byte = bin(byte)[2:].rjust(BYTE_LENGTH, '0')

        for bit in byte:
            bits += bit
            if len(bits) in val_lens:
                bit_str = ''.join(bits)
                decoded_elt = decoder.get(bit_str)
                if decoded_elt:
                    file_output.write(decoded_elt)
                    bits = []
                    input_size -= 1
                    if input_size == 0:
                        break
        byte = file_input.read(1)


def unpack(finput, foutput):
    """Decompress file"""
    fin = open(finput, 'rb')
    fout = open(foutput, 'w')

    input_size, decoder, val_lens = unpack_metadata(fin)
    unpack_data(fin, fout, input_size, decoder, val_lens)

    fin.close()
    fout.close()
