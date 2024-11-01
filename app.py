from flask import Flask, jsonify, request
import os
import json
import logging
import pandas as pd
from datetime import datetime
from Recommend.artwork_recommend import ArtworkRecommender, get_clicked_artworks_for_user, get_artworks_by_ids
from Recommend.utils.debug import save_images

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

def load_configs(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = json.load(f)
    for key, value in config_dict.items():
        if "value" in value:
            config_dict[key] = value["value"]
    return config_dict

user_id = 2
artwork_configs = load_configs("Recommend/configs.json")
artwork_recommender = ArtworkRecommender(user_id=user_id, configs=artwork_configs)

@app.route('/recommend/artwork', methods=['GET'])
def recommend_artwork():
    try:
        behavior_updated = request.args.get("behavior_updated", "false").lower() == "true"
        page_idx = int(request.args.get("page_idx", 0))
        timestamp = int(request.args.get("timestamp", datetime.now().timestamp()))

        context_info = {
            "timestamp": timestamp,
            "behavior_updated": behavior_updated,
            "page_idx": page_idx
        }

        logging.info("Context info received: %s", context_info)
        
        if behavior_updated:
            user_artworks = get_clicked_artworks_for_user(user_id)
            user_log = pd.DataFrame(user_artworks)[["artwork_id", "event_time"]]
            
            result = get_artworks_by_ids(user_log["artwork_id"].tolist())
            if result["status"] == "success" and len(result["data"]) > 0:
                result_df = pd.DataFrame(result["data"])
                filename = f"user_log_{page_idx}"
                
                output_dir = artwork_configs["output_dir"]
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                result_df.to_csv(os.path.join(output_dir, filename + ".csv"), index=False)
                save_images(os.path.join(output_dir, filename + ".jpg"), result_df["artwork_id"], result_df['compressed_url'])
            
            artwork_recommender.update_data(user_log)

        recommendations = artwork_recommender.recommend(context_info)
        
        return jsonify({"status": "success", "data": recommendations}), 200
    except Exception as e:
        logging.error("Error generating recommendations: %s", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
