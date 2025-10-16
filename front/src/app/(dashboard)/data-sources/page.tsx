'use client';

import { useEffect, useState } from 'react';
import { Button, Input, Select, Row, Col } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { useDataSourceStore } from '@/stores/dataSourceStore';
import { DataSourceForm, DataSourceCard } from '@/components/business/data-source';
import { ProtocolType, DataSource } from '@/types/api';
import { MessageHelper } from '@/lib/message';

const { Search } = Input;
const { Option } = Select;

export default function DataSourcesPage() {
  const {
    sources,
    loading,
    error,
    isCreateModalOpen,
    filters,
    fetchSources,
    deleteSource,
    setCreateModalOpen,
    setFilters,
    clearError
  } = useDataSourceStore();

  const [selectedSource, setSelectedSource] = useState<DataSource | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  useEffect(() => {
    fetchSources();
  }, [fetchSources, filters]);

  useEffect(() => {
    if (error) {
      MessageHelper.error(error);
      clearError();
    }
  }, [error, clearError]);

  const handleSearch = (value: string) => {
    setFilters({ search: value });
  };

  const handleProtocolFilter = (value: string) => {
    setFilters({ protocol_type: value || undefined });
  };

  const handleStatusFilter = (value: string) => {
    setFilters({ status: value || undefined });
  };

  const handleEdit = (dataSource: DataSource) => {
    setSelectedSource(dataSource);
    setIsEditModalOpen(true);
  };

  const handleDelete = async (id: string): Promise<boolean> => {
    const success = await deleteSource(id);
    if (!success) {
      MessageHelper.error('数据源删除失败');
    }
    return success;
  };

  const filteredSources = sources.filter(source => {
    if (filters.search && !source.name.toLowerCase().includes(filters.search.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">数据源管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            管理和配置系统中的所有数据源连接
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            icon={<ReloadOutlined />}
            onClick={() => fetchSources()}
            loading={loading}
          >
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
            新增数据源
          </Button>
        </div>
      </div>

      {/* 过滤器 */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <Row gutter={16} align="middle">
          <Col span={8}>
            <Search
              placeholder="搜索数据源名称"
              allowClear
              onSearch={handleSearch}
              onChange={(e) => !e.target.value && handleSearch('')}
            />
          </Col>
          <Col span={4}>
            <Select
              placeholder="协议类型"
              allowClear
              style={{ width: '100%' }}
              onChange={handleProtocolFilter}
            >
              <Option value={ProtocolType.HTTP}>HTTP</Option>
              <Option value={ProtocolType.UDP}>UDP</Option>
              <Option value={ProtocolType.MQTT}>MQTT</Option>
              <Option value={ProtocolType.WEBSOCKET}>WebSocket</Option>
              <Option value={ProtocolType.TCP}>TCP</Option>
            </Select>
          </Col>
          <Col span={4}>
            <Select
              placeholder="连接状态"
              allowClear
              style={{ width: '100%' }}
              onChange={handleStatusFilter}
            >
              <Option value="connected">已连接</Option>
              <Option value="disconnected">未连接</Option>
              <Option value="error">连接异常</Option>
            </Select>
          </Col>
          <Col span={8}>
            <div className="text-sm text-gray-500">
              共 {filteredSources.length} 个数据源
            </div>
          </Col>
        </Row>
      </div>

      {/* 数据源卡片网格 */}
      {filteredSources.length > 0 ? (
        <Row gutter={[16, 16]}>
          {filteredSources.map((source) => (
            <Col key={source.id} xs={24} sm={12} lg={8} xl={6}>
              <DataSourceCard
                dataSource={source}
                onEdit={handleEdit}
                onDelete={handleDelete}
              />
            </Col>
          ))}
        </Row>
      ) : (
        <div className="text-center py-12">
          <div className="text-gray-400 text-6xl mb-4">🔌</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {sources.length === 0 ? '还没有数据源' : '没有找到匹配的数据源'}
          </h3>
          <p className="text-gray-500 mb-6">
            {sources.length === 0
              ? '创建第一个数据源来开始收集数据'
              : '尝试调整筛选条件或搜索关键词'
            }
          </p>
          {sources.length === 0 && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalOpen(true)}
            >
              创建数据源
            </Button>
          )}
        </div>
      )}

      {/* 创建数据源弹窗 */}
      <DataSourceForm
        open={isCreateModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onSuccess={fetchSources}
      />

      {/* 编辑数据源弹窗 */}
      {selectedSource && (
        <DataSourceForm
          open={isEditModalOpen}
          onCancel={() => {
            setIsEditModalOpen(false);
            setSelectedSource(null);
          }}
          dataSource={selectedSource}
          onSuccess={fetchSources}
        />
      )}
    </div>
  );
}
