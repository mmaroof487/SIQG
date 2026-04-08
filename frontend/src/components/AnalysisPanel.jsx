import React, { useState } from 'react';
import { DocumentDuplicateIcon, CheckIcon } from '@heroicons/react/solid';

const AnalysisPanel = ({ analysis }) => {
  const [copiedIndex, setCopiedIndex] = useState(null);

  if (!analysis) {
    return null;
  }

  const {
    index_suggestions,
    recommendation,
    complexity,
    execution_time_ms,
    slow_query,
  } = analysis;

  const copyToClipboard = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="mt-6 space-y-4">
      {/* Recommendation */}
      {recommendation && (
        <div className="border border-purple-200 bg-purple-50 rounded-lg p-4">
          <div className="text-sm font-semibold text-purple-900 mb-2">
            📊 Recommendation
          </div>
          <p className="text-sm text-purple-800">{recommendation}</p>
        </div>
      )}

      {/* Complexity Score */}
      {complexity !== undefined && (
        <div className="border border-purple-200 bg-purple-50 rounded-lg p-4">
          <div className="text-sm font-semibold text-purple-900 mb-2">
            Query Complexity
          </div>
          <div className="flex items-center gap-3">
            <div className="flex-1 bg-gray-200 rounded-full h-3 overflow-hidden">
              <div
                className={`h-full transition ${
                  complexity > 80
                    ? 'bg-red-500'
                    : complexity > 50
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(complexity, 100)}%` }}
              />
            </div>
            <span className="font-semibold text-purple-900 min-w-12">
              {complexity.toFixed(0)}
            </span>
          </div>
          <div className="text-xs text-purple-700 mt-2">
            {complexity > 80
              ? 'High complexity - consider simplifying'
              : complexity > 50
              ? 'Moderate complexity'
              : 'Low complexity - good query structure'}
          </div>
        </div>
      )}

      {/* Execution Time */}
      {execution_time_ms !== undefined && (
        <div className="border border-purple-200 bg-purple-50 rounded-lg p-4">
          <div className="text-sm font-semibold text-purple-900 mb-2">
            Execution Time
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-purple-600">
              {execution_time_ms.toFixed(2)}
            </span>
            <span className="text-gray-600">ms</span>
          </div>
          {slow_query && (
            <div className="text-xs text-red-600 mt-2">
              ⚠️ This query exceeded the slow query threshold.
            </div>
          )}
        </div>
      )}

      {/* Index Suggestions */}
      {index_suggestions && index_suggestions.length > 0 && (
        <div className="border border-green-200 bg-green-50 rounded-lg p-4">
          <div className="text-sm font-semibold text-green-900 mb-3">
            🔍 Index Suggestions ({index_suggestions.length})
          </div>
          <div className="space-y-3">
            {index_suggestions.map((suggestion, idx) => (
              <div key={idx} className="bg-white border border-green-200 rounded p-3">
                <div className="text-xs font-semibold text-gray-700 mb-2">
                  {suggestion.table}.{suggestion.column}
                </div>
                <div className="text-xs text-gray-600 mb-3">
                  {suggestion.reason}
                </div>

                {/* DDL Code Block */}
                <div className="bg-gray-900 text-green-400 rounded p-2 font-mono text-xs mb-2 overflow-auto max-h-20">
                  {suggestion.ddl}
                </div>

                {/* Copy Button */}
                <button
                  onClick={() => copyToClipboard(suggestion.ddl, idx)}
                  className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-3 rounded transition text-sm"
                >
                  {copiedIndex === idx ? (
                    <>
                      <CheckIcon className="h-4 w-4" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <DocumentDuplicateIcon className="h-4 w-4" />
                      Copy DDL
                    </>
                  )}
                </button>

                {/* Improvement Info */}
                <div className="text-xs text-gray-500 mt-2">
                  <strong>Expected improvement:</strong>{' '}
                  {suggestion.estimated_improvement}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No suggestions message */}
      {(!index_suggestions || index_suggestions.length === 0) && !recommendation && (
        <div className="border border-gray-200 bg-gray-50 rounded-lg p-4 text-center">
          <div className="text-sm text-gray-600">
            ✅ No optimization suggestions at this time.
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisPanel;
