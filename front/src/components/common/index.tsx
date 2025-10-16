import { cn } from '@/utils';
import type { BaseComponentProps } from '@/types';

interface LoadingSpinnerProps extends BaseComponentProps {
  size?: 'sm' | 'md' | 'lg';
}

export function LoadingSpinner({ className, size = 'md' }: LoadingSpinnerProps) {
  return (
    <div className={cn('flex justify-center items-center', className)}>
      <svg
        className={cn('animate-spin text-blue-600', {
          'h-4 w-4': size === 'sm',
          'h-6 w-6': size === 'md',
          'h-8 w-8': size === 'lg',
        })}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        ></circle>
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        ></path>
      </svg>
    </div>
  );
}

interface ErrorMessageProps extends BaseComponentProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry, className }: ErrorMessageProps) {
  return (
    <div className={cn('text-center py-8', className)}>
      <div className="text-red-600 mb-4">{message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-blue-600 hover:text-blue-800 underline"
        >
          重试
        </button>
      )}
    </div>
  );
}