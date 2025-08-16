from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from chatbot import GeminiChatbot
import os
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for frontend communication

# Initialize chatbot with API key
chatbot = GeminiChatbot(api_key='AIzaSyD9lkGMYrv3FQopFVgIPEoTXXWczfTRah0')


# Binary Tree Node class
class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None


def build_binary_tree(lines):
    """
    Build a binary tree from lines of text.
    - Headings are root-level nodes.
    - Numbered topics are left children (subtopics).
    - Descriptions are right children.
    """
    if not lines:
        return None

    root = None
    current = None
    prev_topic = None

    for line in lines:
        is_heading = re.match(r'^<b>.*</b>$', line)
        is_numbered_topic = re.match(r'^\d+\.\s', line)

        node = TreeNode(line)

        if is_heading:
            if not root:
                root = node
            else:
                # Attach new heading as a new root, moving previous tree to left
                new_root = node
                new_root.left = root
                root = new_root
            current = root
            prev_topic = None
        elif is_numbered_topic:
            if current:
                if not prev_topic:
                    current.left = node
                else:
                    prev_topic.left = node
                prev_topic = node
                current = node
        else:
            if current:
                current.right = node
                current = node
            prev_topic = None

    return root


def traverse_tree(node, indent=0):
    """
    Traverse the binary tree in-order and format with indentation.
    - Headings get no indent, empty line after.
    - Numbered topics get blank line before, 2-space indent.
    - Descriptions get 4-space indent.
    """
    result = []
    if not node:
        return result

    # Process current node
    is_heading = re.match(r'^<b>.*</b>$', node.value)
    is_numbered_topic = re.match(r'^\d+\.\s', node.value)

    if is_heading:
        result.append(node.value + '\n')
    elif is_numbered_topic:
        result.append('')  # Blank line before numbered topic
        result.append('  ' + node.value)
    else:
        result.append('    ' + node.value)

    # Traverse left (subtopics)
    if node.left:
        result.extend(traverse_tree(node.left, indent + 2))

    # Traverse right (descriptions)
    if node.right:
        result.extend(traverse_tree(node.right, indent + 4))

    return result


def parse_response(raw_response):
    """
    Parse the chatbot response into a binary tree and format for college notes structure.
    - Detect **text** as headings, bold with <b> tags, place on separate line with empty line after.
    - Replace single * with newline for separation.
    - Add blank line before numbered topics (e.g., 1., 2.).
    - Use binary tree to organize hierarchically.
    """
    # Replace **text** with <b>text</b> (no extra spaces)
    processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', raw_response)
    # Replace single * with \n
    processed = re.sub(r'(?<!\*)\*(?!\*)', '\n', processed)
    # Split into lines
    lines = [line.strip() for line in processed.split('\n') if line.strip()]

    # Build binary tree
    root = build_binary_tree(lines)

    # Traverse tree to generate formatted output
    formatted = traverse_tree(root)
    return '\n'.join(formatted)


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get('message', '')
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400
    try:
        # Get the raw response from the chatbot
        response = chatbot.chat.send_message(user_input).text
        # Parse the response with formatting for headings and paragraphs
        formatted_response = parse_response(response)
        return jsonify({'response': formatted_response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/')
def serve_frontend():
    try:
        # Ensure AI.html is in the same directory as app.py or provide the correct path
        file_path = os.path.join(os.path.dirname(__file__), 'AI.html')
        if not os.path.exists(file_path):
            return jsonify({'error': 'AI.html not found'}), 404
        return send_file(file_path)
    except Exception as e:
        return jsonify({'error': f'Failed to serve file: {str(e)}'}), 500


if __name__ == '__main__':

    app.run(debug=True, host='0.0.0.0', port=5000)
