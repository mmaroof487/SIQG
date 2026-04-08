import React from 'react';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/solid';

const QueryDiffViewer = ({ originalQuery, modifiedQuery, isExpanded, onToggle }) => {
  if (!originalQuery || !modifiedQuery) {
    return null;
  }

  // Check if there are actual differences
  const hasDifferences = originalQuery.trim() !== modifiedQuery.trim();

  if (!hasDifferences) {
    return null;
  }

  // Highlight differences in query text
  const highlightDifferences = (text) => {
    // Add spans around changed characters for visual emphasis
    return text;
  };

  return (
    <div className="mt-6 border border-yellow-200 bg-yellow-50 rounded-lg p-4">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between text-left hover:bg-yellow-100 p-2 rounded transition"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronUpIcon className="h-5 w-5 text-yellow-700" />
          ) : (
            <ChevronDownIcon className="h-5 w-5 text-yellow-700" />
          )}
          <h3 className="font-semibold text-yellow-900">
            Query Modifications
          </h3>
        </div>
        <span className="text-sm text-yellow-700 px-2 py-1 bg-yellow-100 rounded">
          Argus made changes
        </span>
      </button>

      {isExpanded && (
        <div className="mt-4 space-y-4">
          {/* Side-by-side comparison */}
          <div className="grid grid-cols-2 gap-4">
            {/* Original Query */}
            <div>
              <div className="text-sm font-semibold text-gray-700 mb-2">
                Original Query
              </div>
              <pre className="bg-white border border-gray-300 rounded p-3 text-xs overflow-auto max-h-48 text-gray-800">
                {originalQuery}
              </pre>
            </div>

            {/* Modified Query */}
            <div>
              <div className="text-sm font-semibold text-green-700 mb-2">
                Modified Query
              </div>
              <pre className="bg-white border border-green-300 rounded p-3 text-xs overflow-auto max-h-48 text-gray-800">
                {modifiedQuery}
              </pre>
            </div>
          </div>

          {/* Summary of changes */}
          <div className="bg-white border border-gray-200 rounded p-3">
            <div className="text-sm font-semibold text-gray-700 mb-2">
              What Changed:
            </div>
            <ul className="text-sm text-gray-700 space-y-1">
              {originalQuery !== modifiedQuery && (
                <>
                  {!originalQuery.toUpperCase().includes('LIMIT') &&
                    modifiedQuery.toUpperCase().includes('LIMIT') && (
                      <li>✓ Added LIMIT clause for safety</li>
                    )}
                  {originalQuery.includes('*') &&
                    !modifiedQuery.includes('*') && (
                      <li>✓ Replaced SELECT * with specific columns</li>
                    )}
                  {originalQuery.toUpperCase().includes(
                    'DELETE'
                  ) && !modifiedQuery.toUpperCase().includes('DELETE') && (
                      <li>✓ Removed dangerous DELETE operation</li>
                    )}
                  {originalQuery.toUpperCase().includes(
                    'DROP'
                  ) && !modifiedQuery.toUpperCase().includes('DROP') && (
                      <li>✓ Removed dangerous DROP operation</li>
                    )}
                  <li>✓ Other SQL normalizations applied</li>
                </>
              )}
            </ul>
          </div>

          {/* Copy button */}
          <div className="flex gap-2">
            <button
              onClick={() => {
                navigator.clipboard.writeText(modifiedQuery);
                alert('Modified query copied to clipboard');
              }}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded transition"
            >
              Copy Modified Query
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default QueryDiffViewer;
