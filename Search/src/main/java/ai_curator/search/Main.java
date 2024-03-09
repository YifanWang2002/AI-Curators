package ai_curator.search;

import java.util.Scanner;

// import org.apache.lucene.demo.IndexFiles;
// import org.apache.lucene.demo.SearchFiles;

import ai_curator.search.Index;
import ai_curator.search.Search;

public class Main {
    public static void main(String[] args) {
        String indexPath = "index";

        if (args.length > 0) {
            if ("--index".equals(args[0])) {
                String dataResourceName = "art_metadata_filtered.csv";
                String embedResourceName = "embeddings_bert_sentence.bin";

                try {
                    Index.index(dataResourceName, embedResourceName, indexPath);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            } else if ("--search".equals(args[0])) {
                try (Scanner scanner = new Scanner(System.in)) {
                    System.out.println("Input your query: ");
                    String userQuery = scanner.nextLine();

                    int numOutputHits = 20;

                    System.out.println("Using Gemini augmentation...");
                    Search.search(userQuery, numOutputHits, indexPath, true);
                    System.out.println();
                    System.out.println("Using no augmentation...");
                    Search.search(userQuery, numOutputHits, indexPath, false);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            } else {
                System.out.println("Wrong argument");
            }
        } else {
            System.out.println("No argument provided.");
        }
    }
}