// 全局类型定义
export interface User {
  id: string;
  username: string;
  fullName?: string;
  email?: string;
  role: string;
  permissions: string[];
  avatar?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  code?: number;
}

export interface PaginationParams {
  page: number;
  limit: number;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

// 表单相关类型
export interface FormFieldProps {
  label?: string;
  error?: string;
  required?: boolean;
}

// 通用组件Props类型
export interface BaseComponentProps {
  className?: string;
  children?: React.ReactNode;
}
