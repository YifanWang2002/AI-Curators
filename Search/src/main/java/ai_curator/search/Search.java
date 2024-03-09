package ai_curator.search;

import java.nio.file.Paths;
import org.json.JSONObject;
import org.json.JSONArray;
import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.StoredFields;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.BooleanClause;
import org.apache.lucene.search.BooleanQuery;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.BoostQuery;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.store.FSDirectory;

import ai_curator.search.Gemini;

public class Search {

    /** Simple command-line based search demo. */
    public static void search(String userQuery, int numOutputHits, String indexPath, boolean augment) throws Exception {
        String field = "analysis";

        try (DirectoryReader reader = DirectoryReader.open(FSDirectory.open(Paths.get(indexPath)))) {
            IndexSearcher searcher = new IndexSearcher(reader);
            Analyzer analyzer = new StandardAnalyzer();
            Query query;

            if (augment) {
                // Augment the query string
                JSONObject jsonObject = Gemini.getGeminiResponse(userQuery);

                if (jsonObject != null) {

                    BooleanQuery.Builder booleanQueryBuilder = new BooleanQuery.Builder();

                    for (String key : jsonObject.keySet()) {
                        // Add the key with weight 1
                        // Escape special characters that influence boolean query syntax
                        Query keyQuery = new QueryParser(field, analyzer).parse(QueryParser.escape(key));
                        booleanQueryBuilder.add(new BooleanClause(keyQuery, BooleanClause.Occur.SHOULD));

                        // Process the synonyms array
                        JSONArray synonyms = jsonObject.getJSONArray(key);
                        float weight = 0.8f; // Start with the highest weight
                        for (int i = 0; i < synonyms.length(); i++) {
                            String synonym = synonyms.getString(i);
                            Query synonymQuery = new QueryParser(field, analyzer).parse(QueryParser.escape(synonym));
                            synonymQuery = new BoostQuery(synonymQuery, weight);
                            booleanQueryBuilder.add(new BooleanClause(synonymQuery, BooleanClause.Occur.SHOULD));

                            weight -= 0.1f; // Decrease the weight for the next term
                            if (weight < 0.1f) { // Ensure the weight doesn't go below 0.1
                                weight = 0.1f;
                            }
                        }
                    }
                    query = booleanQueryBuilder.build();

                } else {
                    query = new QueryParser(field, analyzer).parse(QueryParser.escape((userQuery)));
                }

            } else {
                query = new QueryParser(field, analyzer).parse(QueryParser.escape((userQuery)));
            }

            TopDocs results = searcher.search(query, numOutputHits);
            ScoreDoc[] hits = results.scoreDocs;

            int numTotalHits = Math.toIntExact(results.totalHits.value);
            System.out.println(numTotalHits + " total matching documents");

            StoredFields storedFields = searcher.storedFields();
            for (int i = 0; i < Math.min(numTotalHits, numOutputHits); i++) {
                Document doc = storedFields.document(hits[i].doc);
                System.out.println(doc.get("TITLE") + " | Score: " + hits[i].score);
            }
        }
    }

    // private static Query addSemanticQuery(Query query, KnnVectorDict vectorDict,
    // int k)
    // throws IOException {
    // StringBuilder semanticQueryText = new StringBuilder();
    // QueryFieldTermExtractor termExtractor = new
    // QueryFieldTermExtractor("contents");
    // query.visit(termExtractor);
    // for (String term : termExtractor.terms) {
    // semanticQueryText.append(term).append(' ');
    // }
    // if (semanticQueryText.length() > 0) {
    // KnnFloatVectorQuery knnQuery = new KnnFloatVectorQuery(
    // "contents-vector",
    // new
    // DemoEmbeddings(vectorDict).computeEmbedding(semanticQueryText.toString()),
    // k);
    // BooleanQuery.Builder builder = new BooleanQuery.Builder();
    // builder.add(query, BooleanClause.Occur.SHOULD);
    // builder.add(knnQuery, BooleanClause.Occur.SHOULD);
    // return builder.build();
    // }
    // return query;
    // }

    // private static class QueryFieldTermExtractor extends QueryVisitor {
    // private final String field;
    // private final List<String> terms = new ArrayList<>();

    // QueryFieldTermExtractor(String field) {
    // this.field = field;
    // }

    // @Override
    // public boolean acceptField(String field) {
    // return field.equals(this.field);
    // }

    // @Override
    // public void consumeTerms(Query query, Term... terms) {
    // for (Term term : terms) {
    // this.terms.add(term.text());
    // }
    // }

    // @Override
    // public QueryVisitor getSubVisitor(BooleanClause.Occur occur, Query parent) {
    // if (occur == BooleanClause.Occur.MUST_NOT) {
    // return QueryVisitor.EMPTY_VISITOR;
    // }
    // return this;
    // }
    // }
}