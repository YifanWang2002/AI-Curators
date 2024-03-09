package ai_curator.search;

import com.opencsv.CSVReaderHeaderAware;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class CSVColumnsReader {
    public static Map<String, List<String>> readSelectedColumns(String resourcePath, List<String> columnNames) {
        Map<String, List<String>> columnData = new HashMap<>();

        // Initialize lists for each column name in columnNames
        for (String columnName : columnNames) {
            columnData.put(columnName, new ArrayList<>());
        }

        try (InputStreamReader isr = new InputStreamReader(
                CSVColumnsReader.class.getClassLoader().getResourceAsStream(resourcePath));
                CSVReaderHeaderAware reader = new CSVReaderHeaderAware(isr)) {

            Map<String, String> valueMap;
            while ((valueMap = reader.readMap()) != null) {
                for (String columnName : columnNames) {
                    String value = valueMap.get(columnName);
                    if (value != null) {
                        // Add the value to the corresponding list in the columnData map
                        columnData.get(columnName).add(value);
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        return columnData;
    }

    public static void main(String[] args) {
        String resourcePath = "art_metadata_filtered.csv";
        List<String> columnNames = List.of("TITLE", "AUTHOR", "LOCATION", "analysis");

        Map<String, List<String>> columnData = readSelectedColumns(resourcePath, columnNames);

        // Example: Print out the data, limited to the first 5 data points per column
        for (Map.Entry<String, List<String>> entry : columnData.entrySet()) {
            System.out.print(entry.getKey() + ": ");

            // Get the list of values for the current column
            List<String> values = entry.getValue();

            // Determine the number of values to print (up to 5)
            int printCount = Math.min(values.size(), 5);

            // Print the values
            for (int i = 0; i < printCount; i++) {
                System.out.print(values.get(i));
                if (i < printCount - 1) {
                    System.out.println();
                    System.out.println("============================================");
                }
            }

            // Move to the next line after printing values for the current column
            System.out.println();
        }
    }
}
