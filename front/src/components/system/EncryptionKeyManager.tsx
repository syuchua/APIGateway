'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import type { EncryptionKey } from '@/types/api';

interface FormState {
  name: string;
  description: string;
  isActive: boolean;
}

export function EncryptionKeyManager() {
  const [keys, setKeys] = useState<EncryptionKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>({ name: '', description: '', isActive: false });
  const [creating, setCreating] = useState(false);

  const loadKeys = async () => {
    setLoading(true);
    const response = await apiClient.encryptionKeys.list();
    if (response.success && response.data) {
      setKeys(response.data);
      setError(null);
    } else {
      setError(response.error || '加载密钥失败');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadKeys();
  }, []);

  const handleCreate = async () => {
    if (!form.name.trim()) {
      setError('请输入密钥名称');
      return;
    }

    setCreating(true);
    const response = await apiClient.encryptionKeys.create({
      name: form.name.trim(),
      description: form.description || undefined,
      is_active: form.isActive,
    });

    if (response.success) {
      setForm({ name: '', description: '', isActive: false });
      setError(null);
      await loadKeys();
    } else {
      setError(response.error || '创建密钥失败');
    }
    setCreating(false);
  };

  const handleActivate = async (id: string) => {
    const res = await apiClient.encryptionKeys.activate(id);
    if (!res.success) {
      setError(res.error || '激活失败');
      return;
    }
    await loadKeys();
  };

  const handleDeactivate = async (id: string) => {
    const res = await apiClient.encryptionKeys.deactivate(id);
    if (!res.success) {
      setError(res.error || '停用失败');
      return;
    }
    await loadKeys();
  };

  const handleDelete = async (id: string) => {
    const res = await apiClient.encryptionKeys.delete(id);
    if (!res.success) {
      setError(res.error || '删除失败');
      return;
    }
    await loadKeys();
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900">加密密钥管理</h3>
          <p className="mt-1 text-sm text-gray-500">用于数据加解密的主密钥管理与轮换</p>
        </div>
      </div>

      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">密钥名称</label>
            <input
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="例如: gateway-master"
              value={form.name}
              onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">描述 (可选)</label>
            <input
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="这条密钥的用途"
              value={form.description}
              onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
            />
          </div>
          <label className="inline-flex items-center text-sm text-gray-600">
            <input
              type="checkbox"
              className="mr-2 rounded border-gray-300"
              checked={form.isActive}
              onChange={(event) => setForm((prev) => ({ ...prev, isActive: event.target.checked }))}
            />
            创建后立即激活
          </label>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60"
          >
            {creating ? '创建中...' : '创建密钥'}
          </button>
          {error && <span className="text-sm text-red-600">{error}</span>}
        </div>

        <div className="border rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-sm text-gray-500">
                    正在加载...
                  </td>
                </tr>
              ) : keys.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-sm text-gray-500">
                    暂无密钥，请先创建
                  </td>
                </tr>
              ) : (
                keys.map((key) => (
                  <tr key={key.id}>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      <div className="font-medium">{key.name}</div>
                      {key.description && <div className="text-xs text-gray-500">{key.description}</div>}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex px-2 py-0.5 text-xs rounded-full ${
                          key.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {key.is_active ? '已激活' : '未激活'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(key.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 space-x-2">
                      {key.is_active ? (
                        <button
                          onClick={() => handleDeactivate(key.id)}
                          className="text-orange-600 hover:text-orange-800"
                        >
                          停用
                        </button>
                      ) : (
                        <button
                          onClick={() => handleActivate(key.id)}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          激活
                        </button>
                      )}
                      {!key.is_active && (
                        <button
                          onClick={() => handleDelete(key.id)}
                          className="text-red-600 hover:text-red-800"
                        >
                          删除
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
