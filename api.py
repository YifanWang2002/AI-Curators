import json
import logging
import os
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, request
from flask_cors import CORS
from redis import Redis
from rq import Queue
from utils.auth_utils import require_auth

from app import process_exhibition
from config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# 初始化Redis和RQ
redis_conn = Redis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=Config.REDIS_DB,
    password=Config.REDIS_PASSWORD,
    decode_responses=True
)
queue = Queue(Config.RQ_QUEUE_NAME, connection=redis_conn)

def handle_errors(f):
    """Error handling decorator"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            return jsonify({'error': str(e)}), 500
    return wrapper

@app.route('/api/exhibition/create', methods=['POST'])
@require_auth
@handle_errors
def create_exhibition(token_data, user_id):
    """Initialize exhibition generation process"""
    request_data = request.get_json()
    if not request_data or 'prompt' not in request_data:
        return jsonify({'error': 'No prompt provided'}), 400
    
    prompt = request_data['prompt']
    curator_id = user_id
    task_id = str(uuid.uuid4())
    
    # 存储初始状态
    redis_conn.setex(
        f'exhibition:task:{task_id}',
        Config.REDIS_EXPIRE_TIME,
        json.dumps({
            'status': 'processing',
            'created_at': str(datetime.now()),
            'prompt': prompt,
            'curator_id': curator_id
        })
    )
    
    # 将任务加入队列
    queue.enqueue(
        process_exhibition,
        prompt,
        task_id,
        curator_id,  # Pass curator_id to process_exhibition
        job_timeout='30m'
    )
    
    return jsonify({
        'task_id': task_id,
        'status': 'processing'
    }), 202

@app.route('/api/exhibition/status/<task_id>', methods=['GET'])
@handle_errors
def get_status(task_id):
    """Get task status and results"""
    task_data = redis_conn.get(f'exhibition:task:{task_id}')
    
    if not task_data:
        return jsonify({'error': 'Task not found'}), 404
    
    status_data = json.loads(task_data)
    return jsonify(status_data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)