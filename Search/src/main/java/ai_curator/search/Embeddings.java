package ai_curator.search;

import java.io.*;

public class Embeddings {

    private int numVectors;
    private int dim;
    private final String resourceName;

    public Embeddings(String resourceName) throws IOException {
        this.resourceName = resourceName;
        try (InputStream is = Embeddings.class.getClassLoader().getResourceAsStream(resourceName)) {
            if (is == null) {
                throw new FileNotFoundException("Resource not found: " + resourceName);
            }
            try (DataInputStream dis = new DataInputStream(is)) {
                this.numVectors = dis.readInt(); // Read number of vectors
                this.dim = dis.readInt(); // Read vector dimension
            }
        }
        System.out.println("Embeddings Loaded. #Embeddings: " + this.numVectors + ", Dim: " + this.dim);
    }

    public float[] loadEmbedding(int index) throws IOException {
        if (index < 0 || index >= numVectors) {
            throw new IndexOutOfBoundsException("Requested embedding index is out of bounds.");
        }

        float[] embedding = new float[dim];
        try (InputStream is = Embeddings.class.getClassLoader().getResourceAsStream(resourceName)) {
            if (is == null) {
                throw new FileNotFoundException("Resource not found: " + resourceName);
            }
            try (DataInputStream dis = new DataInputStream(is)) {
                // Skip to the requested embedding
                long skipBytes = 4L * dim * index + 8; // 4 bytes per float, plus 8 bytes for the header
                dis.skipBytes((int) skipBytes);

                // Read the requested embedding
                for (int j = 0; j < dim; j++) {
                    embedding[j] = dis.readFloat();
                }
            }
        }
        return embedding;
    }

    public int getNumVectors() {
        return numVectors;
    }

    public int getDim() {
        return dim;
    }

    public static void main(String[] args) {
        String resourceName = "embeddings_bert_sentence.bin";
        try {
            Embeddings embeddings = new Embeddings(resourceName);
            int index = 0; // Specify the index of the embedding you want to load
            float[] embedding = embeddings.loadEmbedding(index);

            // Print the first and last 10 elements of the specified embedding
            System.out.print("First 10 elements of embedding " + index + ": ");
            for (int i = 0; i < Math.min(10, embeddings.getDim()); i++) {
                System.out.print(embedding[i] + (i < Math.min(10, embeddings.getDim()) - 1 ? ", " : "\n"));
            }
            System.out.print("Last 10 elements of embedding " + index + ": ");
            for (int i = Math.max(0, embeddings.getDim() - 10); i < embeddings.getDim(); i++) {
                System.out.print(embedding[i] + (i < embeddings.getDim() - 1 ? ", " : "\n"));
            }

        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
