import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  X, 
  Plus, 
  MessageSquare, 
  Send, 
  Trash2,
  Edit3,
  Save,
  X as XIcon
} from 'lucide-react';

function ChatSidebar({ 
  conversations, 
  selectedConversation, 
  onConversationSelect, 
  onClose, 
  onConversationsUpdate 
}) {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [editingTitle, setEditingTitle] = useState(null);
  const [newTitle, setNewTitle] = useState('');

  useEffect(() => {
    if (selectedConversation) {
      loadMessages(selectedConversation.id);
    } else {
      setMessages([]);
    }
  }, [selectedConversation]);

  const loadMessages = async (conversationId) => {
    try {
      const response = await axios.get(`/conversations/${conversationId}/messages`);
      setMessages(response.data);
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  const createNewConversation = async () => {
    try {
      const response = await axios.post('/conversations', {
        title: 'New Conversation',
        ta_id: 1
      });
      onConversationsUpdate();
      onConversationSelect(response.data);
    } catch (error) {
      console.error('Error creating conversation:', error);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation) return;

    setLoading(true);
    try {
      const userMessage = {
        content: newMessage,
        is_ai: false,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, userMessage]);
      setNewMessage('');

      await axios.post(`/conversations/${selectedConversation.id}/messages`, {
        content: newMessage,
        is_ai: false
      });

      const aiResponse = await axios.post(`/conversations/${selectedConversation.id}/messages`, {
        content: 'Generate a helpful response to: ' + newMessage,
        is_ai: true
      });

      setMessages(prev => [...prev, aiResponse.data]);
    } catch (error) {
      console.error('Error sending message:', error);
    }
    setLoading(false);
  };

  return (
    <div className="w-96 bg-white border-l border-gray-200 flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Conversations</h2>
        <div className="flex items-center space-x-2">
          <button
            onClick={createNewConversation}
            className="p-2 text-gray-400 hover:text-gray-600"
          >
            <Plus className="h-5 w-5" />
          </button>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <MessageSquare className="h-12 w-12 mx-auto mb-2 text-gray-300" />
            <p>No conversations yet</p>
            <button
              onClick={createNewConversation}
              className="mt-2 text-primary-600 hover:text-primary-700 text-sm"
            >
              Start your first conversation
            </button>
          </div>
        ) : (
          <div className="p-2">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`p-3 rounded-lg cursor-pointer transition-colors ${
                  selectedConversation?.id === conversation.id
                    ? 'bg-primary-50 border border-primary-200'
                    : 'hover:bg-gray-50'
                }`}
                onClick={() => onConversationSelect(conversation)}
              >
                <div className="text-sm font-medium text-gray-900 truncate">
                  {conversation.title}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {new Date(conversation.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedConversation && (
        <div className="border-t border-gray-200 flex flex-col h-96">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.is_ai ? 'justify-start' : 'justify-end'}`}
              >
                <div
                  className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                    message.is_ai
                      ? 'bg-gray-100 text-gray-900'
                      : 'bg-primary-600 text-white'
                  }`}
                >
                  <p className="text-sm">{message.content}</p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 text-gray-900 px-4 py-2 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                    <span className="text-sm">AI is thinking...</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="p-4 border-t border-gray-200">
            <div className="flex space-x-2">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Type your message..."
                className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                disabled={loading}
              />
              <button
                onClick={sendMessage}
                disabled={!newMessage.trim() || loading}
                className="px-3 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ChatSidebar; 