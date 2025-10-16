'use client';

import React, { Suspense, use } from 'react';
import { Button, Card, Badge, Spin, Alert } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined } from '@ant-design/icons';

interface ConnectionTestResult {
  success: boolean;
  message: string;
  latency?: number;
  details?: Record<string, unknown>;
}

interface DataSourceConnectionTestProps {
  dataSourceId: string;
  onTest?: (result: ConnectionTestResult) => void;
}

// 模拟连接测试API调用
async function testDataSourceConnection(): Promise<ConnectionTestResult> {
  // 模拟网络延迟
  await new Promise(resolve => setTimeout(resolve, 2000));

  // 模拟随机结果
  const isSuccess = Math.random() > 0.3;

  if (isSuccess) {
    return {
      success: true,
      message: '连接测试成功',
      latency: Math.floor(Math.random() * 100) + 10,
      details: {
        endpoint: 'api.example.com:8080',
        protocol: 'HTTP',
        timestamp: new Date().toISOString(),
      }
    };
  } else {
    return {
      success: false,
      message: '连接超时或服务不可达',
      details: {
        error: 'ECONNREFUSED',
        attempts: 3,
        lastAttempt: new Date().toISOString(),
      }
    };
  }
}

// 使用React 19的use() Hook来处理异步数据
function ConnectionTestResult({ testPromise }: { testPromise: Promise<ConnectionTestResult> }) {
  const result = use(testPromise);

  return (
    <Card className="mt-4">
      <div className="flex items-center gap-3">
        {result.success ? (
          <CheckCircleOutlined className="text-green-500 text-xl" />
        ) : (
          <CloseCircleOutlined className="text-red-500 text-xl" />
        )}

        <div className="flex-1">
          <div className="flex items-center gap-2">
            <Badge
              status={result.success ? "success" : "error"}
              text={result.message}
            />
            {result.latency && (
              <span className="text-gray-500 text-sm">
                延迟: {result.latency}ms
              </span>
            )}
          </div>

          {result.details && (
            <div className="mt-2 text-sm text-gray-600">
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(result.details).map(([key, value]) => (
                  <div key={key}>
                    <span className="font-medium">{key}:</span> {String(value)}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

// 加载状态组件
function TestingLoadingFallback() {
  return (
    <Card className="mt-4">
      <div className="flex items-center gap-3 py-2">
        <Spin indicator={<LoadingOutlined className="text-blue-500" spin />} />
        <span className="text-gray-600">正在测试连接...</span>
      </div>
    </Card>
  );
}

export function DataSourceConnectionTest({ dataSourceId: _dataSourceId, onTest }: DataSourceConnectionTestProps) {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _ = _dataSourceId;
  const [testPromise, setTestPromise] = React.useState<Promise<ConnectionTestResult> | null>(null);
  const [hasStartedTest, setHasStartedTest] = React.useState(false);

  const handleTestConnection = () => {
    setHasStartedTest(true);
    const promise = testDataSourceConnection();
    setTestPromise(promise);

    // 可选：当测试完成时调用回调
    if (onTest) {
      promise.then(onTest);
    }
  };

  const handleRetryTest = () => {
    setTestPromise(null);
    // 短暂延迟后重新测试
    setTimeout(() => {
      handleTestConnection();
    }, 100);
  };

  return (
    <div>
      <div className="flex items-center gap-3">
        <Button
          type="primary"
          onClick={handleTestConnection}
          disabled={!!testPromise}
        >
          测试连接
        </Button>

        {hasStartedTest && (
          <Button
            onClick={handleRetryTest}
            disabled={!!testPromise}
          >
            重新测试
          </Button>
        )}
      </div>

      {testPromise && (
        <Suspense fallback={<TestingLoadingFallback />}>
          <ConnectionTestResult testPromise={testPromise} />
        </Suspense>
      )}

      {!hasStartedTest && (
        <Alert
          message="点击上方按钮测试数据源连接"
          type="info"
          showIcon
          className="mt-4"
        />
      )}
    </div>
  );
}