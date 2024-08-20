package ai_curator.search;

import java.io.IOException;
import java.nio.file.Paths;
import java.util.Date;
import java.util.List;
import java.util.Map;

import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.KnnFloatVectorField;
import org.apache.lucene.document.TextField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.index.IndexWriterConfig.OpenMode;
import org.apache.lucene.index.VectorSimilarityFunction;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;

import ai_curator.search.CSVColumnsReader;
import ai_curator.search.Embeddings;

public class Index {

    public static void index(String dataResourceName, String embedResourceName, String indexPath) throws Exception {
        Date start = new Date();
        try {
            System.out.println("Indexing to directory '" + indexPath + "'...");

            Directory dir = FSDirectory.open(Paths.get(indexPath));
            Analyzer analyzer = new StandardAnalyzer();
            IndexWriterConfig iwc = new IndexWriterConfig(analyzer);
            iwc.setOpenMode(OpenMode.CREATE);

            try (IndexWriter writer = new IndexWriter(dir, iwc)) {
                Index.indexDocs(writer, dataResourceName, embedResourceName);
            }

            Date end = new Date();
            try (IndexReader reader = DirectoryReader.open(dir)) {
                System.out.println(
                        "Indexed "
                                + reader.numDocs()
                                + " documents in "
                                + (end.getTime() - start.getTime())
                                + " ms");
            }
        } catch (IOException e) {
            System.out.println(" caught a " + e.getClass() + "\n with message: " + e.getMessage());
        }
    }

    private static void indexDocs(final IndexWriter writer, String dataResourceName, String embedResourceName)
            throws IOException {

        List<String> columnNames = List.of("TITLE", "AUTHOR", "LOCATION", "analysis");

        Map<String, List<String>> columnData = CSVColumnsReader.readSelectedColumns(dataResourceName, columnNames);

        int numOfDocs = columnData.values().iterator().next().size();

        Embeddings embeddings = new Embeddings(embedResourceName);

        for (int i = 0; i < numOfDocs; i++) {
            Document doc = new Document();

            for (Map.Entry<String, List<String>> entry : columnData.entrySet()) {
                String fieldName = entry.getKey();
                List<String> values = entry.getValue();

                String fieldValue = values.get(i);
                doc.add(new TextField(fieldName, fieldValue, Field.Store.YES));
            }
            doc.add(
                    new KnnFloatVectorField(
                            "embedding", embeddings.loadEmbedding(i), VectorSimilarityFunction.DOT_PRODUCT));

            writer.addDocument(doc);
        }
    }

}
