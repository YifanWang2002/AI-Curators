package ai_curator.search;

import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import org.json.JSONObject;
import org.json.JSONArray;

public class Gemini {
    public static JSONObject getGeminiResponse(String userQuery) {
        try {
            // Define the URL and API key
            String apiKey = System.getenv("GEMINI_API_KEY");
            URL url = new URL(
                    "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key=" + apiKey);

            // Create the connection
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Content-Type", "application/json");

            // Enable input and output streams
            connection.setDoOutput(true);

            String newText = "You will be given a user's search query on an art image platform. Output the keywords in the original query with their synonyms. The synonyms should be ranked in the descending order of their relevance to the original query. Examples:\n"
                    +
                    "Query 1: sadness 19 century paintings. Output 1: {\"sadness\": [\"sad\", \"sorrow\", \"sorrowful\", \"melancholy\", \"unhappiness\", \"despair\", \"depression\"], \"19 century\": [\"19th century\", \"nineteenth century\"]}\n"
                    +
                    "Query 2: show me pictures of fruit having vibrant colors. Output 2: {\"fruit\": [\"apple\", \"banana\", \"peach\", \"pear\", \"orange\", \"plant\", \"vegetable\"], \"vibrant colors\": [\"bright colors\", \"vivid colors\", \"radiant colors\", \"intense colors\", \"rich colors\", \"bold colors\", \"luminous colors\", \"dynamic colors\", \"vibrant hues\"]}\n"
                    +
                    "Query: " + userQuery + ". Provide your output in the same json format as the example outputs.";

            String requestBody = "{\"contents\":[{\"role\": \"user\",\"parts\":[{\"text\": \""
                    + newText.replace("\"", "\\\"") + "\"}]}]}";

            // Send the request
            DataOutputStream outputStream = new DataOutputStream(connection.getOutputStream());
            outputStream.writeBytes(requestBody);
            outputStream.flush();
            outputStream.close();

            // Read the response
            BufferedReader inputStream = new BufferedReader(new InputStreamReader(connection.getInputStream()));
            String inputLine;
            StringBuilder response = new StringBuilder();
            while ((inputLine = inputStream.readLine()) != null) {
                response.append(inputLine);
            }
            inputStream.close();

            // Parse the response JSON
            JSONObject jsonResponse = new JSONObject(response.toString());
            JSONArray candidates = jsonResponse.getJSONArray("candidates");
            JSONObject content = candidates.getJSONObject(0).getJSONObject("content");
            JSONArray parts = content.getJSONArray("parts");
            String text = parts.getJSONObject(0).getString("text");
            JSONObject jsonObject = extractJsonPart(text);

            // TODO: delete
            if (jsonObject != null) {
                System.out.println(jsonObject.toString(4));
            } else {
                System.out.println("No JSON detected.");
            }

            return jsonObject;
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    private static JSONObject extractJsonPart(String text) {
        // Simple regex to match from the first { to the last }
        String jsonPattern = "\\{.*\\}";
        java.util.regex.Pattern pattern = java.util.regex.Pattern.compile(jsonPattern, java.util.regex.Pattern.DOTALL);
        java.util.regex.Matcher matcher = pattern.matcher(text);

        // Check if any match is found
        if (matcher.find()) {
            String potentialJson = matcher.group();
            try {
                // Try to parse the matched substring as a JSONObject
                JSONObject jsonObject = new JSONObject(potentialJson);

                // Validate the JSONObject
                if (isValidJsonObject(jsonObject)) {
                    return jsonObject;
                } else {
                    return null;
                }
            } catch (Exception ignored) {
                return null;
            }
        }
        return null;
    }

    private static boolean isValidJsonObject(JSONObject jsonObject) {
        //
        for (String key : jsonObject.keySet()) {
            if (!(jsonObject.get(key) instanceof JSONArray)) {
                return false; // Each value must be a JSONArray
            }
            JSONArray jsonArray = jsonObject.getJSONArray(key);
            for (int i = 0; i < jsonArray.length(); i++) {
                if (!(jsonArray.get(i) instanceof String)) {
                    return false; // Each element in the JSONArray must be a String
                }
            }
        }
        return true; // Passed all checks
    }

    public static void main(String[] args) {
        String userQuery = "river bank woman";
        JSONObject jsonObject = getGeminiResponse(userQuery);
    }
}