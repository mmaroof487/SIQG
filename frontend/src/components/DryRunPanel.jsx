import React from 'react';
import { ExclamationIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/solid';

const DryRunPanel = ({ dryRunResult, isLoading }) => {
  if (!dryRunResult && !isLoading) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="mt-6 border border-blue-200 bg-blue-50 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <div className="animate-spin">
            <ExclamationIcon className="h-5 w-5 text-blue-600" />
          </div>
          <span className="text-blue-700">Analyzing query (dry-run mode)...</span>
        </div>
      </div>
    );
  }

  const {
    would_execute,
    cost_estimate,
    pipeline_checks,
    warnings,
    errors,
  } = dryRunResult;

  return (
    <div className="mt-6 border border-blue-200 bg-blue-50 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-blue-900 flex items-center gap-2">
          <ExclamationIcon className="h-5 w-5" />
          Dry-Run Analysis (No Data Modified)
        </h3>
        <span className="text-xs font-semibold px-2 py-1 bg-blue-100 text-blue-700 rounded">
          Preview Mode
        </span>
      </div>

      {/* Execution Status */}
      <div className="bg-white border border-blue-200 rounded p-3">
        <div className="text-sm font-semibold text-gray-700 mb-2">
          Execution Status
        </div>
        <div className="flex items-center gap-2">
          {would_execute ? (
            <>
              <CheckCircleIcon className="h-5 w-5 text-green-600" />
              <span className="text-green-700">Query would execute successfully</span>
            </>
          ) : (
            <>
              <XCircleIcon className="h-5 w-5 text-red-600" />
              <span className="text-red-700">Query would be blocked</span>
            </>
          )}
        </div>
      </div>

      {/* Cost Estimate */}
      {cost_estimate !== undefined && (
        <div className="bg-white border border-blue-200 rounded p-3">
          <div className="text-sm font-semibold text-gray-700 mb-2">
            Estimated Cost
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-blue-600">
              {cost_estimate.toFixed(0)}
            </span>
            <span className="text-gray-600">cost units</span>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            This query would use approximately {cost_estimate} cost units from your daily budget.
          </div>
        </div>
      )}

      {/* Pipeline Checks */}
      {pipeline_checks && pipeline_checks.length > 0 && (
        <div className="bg-white border border-blue-200 rounded p-3">
          <div className="text-sm font-semibold text-gray-700 mb-3">
            Pipeline Checks ({pipeline_checks.length})
          </div>
          <ul className="space-y-2">
            {pipeline_checks.map((check, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <CheckCircleIcon className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                <span className="text-sm text-gray-700">{check}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
          <div className="text-sm font-semibold text-yellow-900 mb-2">
            ⚠️ Warnings ({warnings.length})
          </div>
          <ul className="space-y-1">
            {warnings.map((warning, idx) => (
              <li key={idx} className="text-sm text-yellow-800">
                • {warning}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Errors */}
      {errors && errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <div className="text-sm font-semibold text-red-900 mb-2">
            ❌ Errors ({errors.length})
          </div>
          <ul className="space-y-1">
            {errors.map((error, idx) => (
              <li key={idx} className="text-sm text-red-800">
                • {error}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Info */}
      <div className="bg-blue-100 border border-blue-200 rounded p-3 text-sm text-blue-800">
        <strong>💡 Tip:</strong> Dry-run mode shows what would happen without actually executing the query. Click "Execute" to run it for real.
      </div>
    </div>
  );
};

export default DryRunPanel;
