import struct
import numpy as np


def convert_npy_to_binary(input_npy_path, output_binary_path):
    # Load the embeddings from the .npy file
    embeddings = np.load(input_npy_path)

    # Ensure embeddings is a 2D array
    if embeddings.ndim != 2:
        raise ValueError("Embeddings should be a 2D array")

    print(embeddings[0][:10])
    print(embeddings[0][-10:])

    num_embeddings, dim = embeddings.shape

    # Open the output file in binary write mode
    with open(output_binary_path, "wb") as f:
        # Write the number of embeddings (as 4-byte integer)
        f.write(num_embeddings.to_bytes(4, byteorder="big"))

        # Write the dimensionality of the embeddings (as 4-byte integer)
        f.write(dim.to_bytes(4, byteorder="big"))

        # Write the embedding values as floats
        for embedding in embeddings:
            for value in embedding:
                # Convert the float to bytes and write it to the file
                f.write(bytearray(struct.pack(">f", value)))


# Example usage
input_npy_path = "data/embeddings_bert_sentence.npy"
output_binary_path = "src/main/resources/embeddings_bert_sentence.bin"
convert_npy_to_binary(input_npy_path, output_binary_path)
