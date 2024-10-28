from flask import Flask, jsonify
from redis import Redis
from rq import Queue
import pandas as pd
from datetime import datetime
import json
import logging
from prompt_based_exhibition.ArtSearch import ArtSearch
from prompt_based_exhibition.prompt_parser_beta import EntityParser
from prompt_based_exhibition.exhibition_curator import ExhibitionCurator
from config import Config
import os
import data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_exhibition(prompt: str, redis_conn, task_id: str) -> None:
    """Worker function for processing exhibition generation"""
    try:
        
        art_search = ArtSearch(data_dir=os.path.join(Config.MODULE_DIR, 'data'))
        entity_parser = EntityParser()
        
        # 更新状态：开始解析prompt
        update_status(redis_conn, task_id, 'parsing_prompt')
        
        # 解析prompt获取tags和artists
        tags, artists = entity_parser.extract_entities(prompt)
        
        # 更新状态：开始搜索艺术品
        update_status(redis_conn, task_id, 'searching_artworks')
        
        # 搜索标签和艺术家
        tag_results = pd.DataFrame()
        name_results = pd.DataFrame()
        
        if tags:
            tag_results = pd.DataFrame(
                art_search.search(tags, search_type='tag', k=20),
                columns=['tag_name', 'similarity']
            )
        if artists:
            name_results = pd.DataFrame(
                art_search.search(artists, search_type='name', k=1),
                columns=['artist_name', 'similarity']
            )

        # 获取artwork详情并处理
        artwork_details = art_search.get_artwork_details()
        if artwork_details.empty:
            raise Exception("Unable to retrieve artwork details from database")

        # 使用你原有的过滤逻辑
        filtered_artwork = filter_artworks(artwork_details, tag_results, name_results, artists)
        
        # 更新状态：展示初始图片集
        update_status(redis_conn, task_id, 'images_selected', {
            'artwork_ids': filtered_artwork['artwork_id'].tolist(),
            'image_urls': filtered_artwork['image_url'].tolist()  # 假设存在image_url列
        })
        
        # 生成展览
        curator = ExhibitionCurator(metadata=artwork_details)
        use_author = bool(artists)
        exhibitions = curator.curate(filtered_artwork, prompt, use_author)
        
        # 更新状态：完成
        update_status(redis_conn, task_id, 'completed', {
            'exhibitions': exhibitions[:3]  # 只返回前三个展览
        })
        
    except Exception as e:
        logger.error(f"Error processing exhibition: {str(e)}")
        update_status(redis_conn, task_id, 'error', {'error': str(e)})
        raise

def update_status(redis_conn, task_id: str, status: str, data: dict = None) -> None:
    """Helper function to update task status in Redis"""
    task_key = f'exhibition:task:{task_id}'
    current_data = {
        'status': status,
        'updated_at': str(datetime.now())
    }
    if data:
        current_data.update(data)
    
    redis_conn.setex(
        task_key,
        Config.REDIS_EXPIRE_TIME,
        json.dumps(current_data)
    )

def filter_artworks(artwork_details: pd.DataFrame, tag_results: pd.DataFrame, 
                   name_results: pd.DataFrame, artists: list) -> pd.DataFrame:
    """Filter artworks based on search results"""
    # Prepare metadata with proper index
    artwork_details = prepare_metadata(artwork_details)
    
    # Filter artwork based on search results
    if artists and not name_results.empty:
        new_artwork = get_artwork_by_artist(artwork_details, name_results)
        if not tag_results.empty:
            temp_artwork = get_artwork_by_tags(tag_results, new_artwork)
            if temp_artwork.shape[0] >= 20:
                new_artwork = temp_artwork
    elif not tag_results.empty:
        new_artwork = get_artwork_by_tags(tag_results, artwork_details)
    else:
        new_artwork = artwork_details.sample(n=min(50, len(artwork_details)))
    
    # Prepare and limit results
    new_artwork = prepare_metadata(new_artwork)
    return new_artwork.iloc[:50]  # Limit to 50 artworks

def prepare_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare metadata DataFrame with proper index and columns"""
    df = df.reset_index(drop=True)
    df['index'] = df.index
    
    required_columns = [
        'index', 'artwork_id', 'artist_given_name', 'artist_family_name',
        'artwork_name', 'artwork_date', 'artwork_type', 'artwork_material'
    ]
    
    for col in required_columns:
        if col not in df.columns:
            df[col] = ''
            
    return df

def get_artwork_by_artist(artwork_details: pd.DataFrame, artist_results: pd.DataFrame) -> pd.DataFrame:
    """Filter artwork details based on artist search results"""
    artwork_details['name'] = artwork_details['artist_given_name'].fillna('') + " " + artwork_details['artist_family_name'].fillna('')
    artwork_details['name'] = artwork_details['name'].str.lower()
    artist_results['artist_name'] = artist_results['artist_name'].str.lower()
    return artwork_details[artwork_details['name'] == artist_results['artist_name'].iloc[0]]

def get_artwork_by_tags(search_results: pd.DataFrame, artwork_df: pd.DataFrame) -> pd.DataFrame:
    """Filter artwork details based on tag search results using MongoDB data"""
    tag_mapping = data.get_tag_mapping()
    if tag_mapping.empty:
        logger.warning("No tag mapping data available")
        return artwork_df
    
    results = search_results.merge(tag_mapping[['tag_id', 'tag_name']], on='tag_name', how='left')
    
    artwork_ids = set()
    for tag_id in results['tag_id'].dropna():
        response = data.get_artwork_by_tag_id(int(tag_id))
        if response.get('status') == 'success':
            artwork_ids.update(response['data'])
    
    if not artwork_ids:
        logger.warning("No artwork IDs found for the given tags")
        return artwork_df
    
    return artwork_df[artwork_df['artwork_id'].isin(artwork_ids)]