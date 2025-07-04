import React, { useEffect, useState } from 'react';
import axios from 'axios';

// Helper: build tree from flat list
function buildTree(flatList) {
  const idMap = {};
  const roots = [];
  flatList.forEach(item => {
    idMap[item.id] = { ...item, children: [] };
  });
  flatList.forEach(item => {
    if (item.parent_id) {
      idMap[item.parent_id].children.push(idMap[item.id]);
    } else {
      roots.push(idMap[item.id]);
    }
  });
  return roots;
}

export default function TATreeSelect({ value, onChange }) {
  const [tas, setTAs] = useState([]);
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    axios.get('/therapeutic-areas').then(res => {
      setTAs(buildTree(res.data));
    });
  }, []);

  const toggle = id => setExpanded(e => ({ ...e, [id]: !e[id] }));

  function renderNode(node, depth = 0) {
    const isSelected = value === node.id;
    const hasChildren = node.children && node.children.length > 0;
    return (
      <div key={node.id} className={`pl-${depth * 4} py-1`}> {/* Indent by depth */}
        <div className={`flex items-center cursor-pointer ${isSelected ? 'bg-primary-100 text-primary-800 font-semibold rounded' : ''}`}
          onClick={() => onChange(node.id)}>
          {hasChildren && (
            <button
              type="button"
              className="mr-1 text-xs text-primary-600 focus:outline-none"
              onClick={e => { e.stopPropagation(); toggle(node.id); }}
            >
              {expanded[node.id] ? '▼' : '▶'}
            </button>
          )}
          <span>{node.name}</span>
        </div>
        {hasChildren && expanded[node.id] && (
          <div className="ml-4 border-l border-primary-100 pl-2">
            {node.children.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded shadow p-2 max-h-64 overflow-y-auto w-72">
      {tas.length === 0 ? (
        <div className="text-gray-400 text-sm">Loading...</div>
      ) : (
        tas.map(node => renderNode(node))
      )}
    </div>
  );
} 