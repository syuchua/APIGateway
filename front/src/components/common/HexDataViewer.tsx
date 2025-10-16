'use client';

import React, { useState, useMemo } from 'react';
import { Card, Input, Button, Space, Switch, Alert, Tag, Tooltip } from 'antd';
import { CopyOutlined, ClearOutlined, DownloadOutlined, EyeOutlined } from '@ant-design/icons';

const { TextArea } = Input;

interface HexViewerProps {
  data?: string;
  title?: string;
  showAscii?: boolean;
  showOffsets?: boolean;
  bytesPerRow?: number;
  editable?: boolean;
  onDataChange?: (data: string) => void;
  highlightRanges?: Array<{
    start: number;
    end: number;
    color: string;
    label: string;
  }>;
}

export function HexDataViewer({
  data = '',
  title = '十六进制数据查看器',
  showAscii: initialShowAscii = true,
  showOffsets: initialShowOffsets = true,
  bytesPerRow: initialBytesPerRow = 16,
  editable = true,
  onDataChange,
  highlightRanges = []
}: HexViewerProps) {
  const [hexData, setHexData] = useState(data);
  const [inputMode, setInputMode] = useState<'hex' | 'text'>('hex');
  const [showOptions, setShowOptions] = useState(false);
  const [showAscii, setShowAscii] = useState(initialShowAscii);
  const [showOffsets, setShowOffsets] = useState(initialShowOffsets);
  const [bytesPerRow, setBytesPerRow] = useState(initialBytesPerRow);

  // 清理和格式化十六进制数据
  const cleanHexData = useMemo(() => {
    return hexData.replace(/[^0-9A-Fa-f]/g, '').toUpperCase();
  }, [hexData]);

  // 验证十六进制数据
  const isValidHex = useMemo(() => {
    if (!cleanHexData) return true;
    return cleanHexData.length % 2 === 0 && /^[0-9A-F]*$/.test(cleanHexData);
  }, [cleanHexData]);

  // 将十六进制转换为字节数组
  const hexToBytes = useMemo(() => {
    if (!isValidHex || !cleanHexData) return [];
    const bytes = [];
    for (let i = 0; i < cleanHexData.length; i += 2) {
      bytes.push(cleanHexData.substr(i, 2));
    }
    return bytes;
  }, [cleanHexData, isValidHex]);

  // 将字节转换为ASCII字符
  const byteToAscii = (hex: string) => {
    const code = parseInt(hex, 16);
    if (code >= 32 && code <= 126) {
      return String.fromCharCode(code);
    }
    return '.';
  };

  // 获取字节的高亮颜色
  const getByteHighlight = (byteIndex: number) => {
    for (const range of highlightRanges) {
      if (byteIndex >= range.start && byteIndex <= range.end) {
        return {
          backgroundColor: range.color,
          color: 'white',
          title: range.label
        };
      }
    }
    return null;
  };

  // 渲染十六进制视图
  const renderHexView = () => {
    if (!isValidHex) {
      return (
        <Alert
          message="数据格式错误"
          description="十六进制数据格式不正确，请检查输入"
          type="error"
          showIcon
        />
      );
    }

    if (hexToBytes.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          <p>暂无数据</p>
          <p className="text-sm">在上方输入十六进制数据</p>
        </div>
      );
    }

    const rows = [];
    for (let i = 0; i < hexToBytes.length; i += bytesPerRow) {
      const rowBytes = hexToBytes.slice(i, i + bytesPerRow);
      const offsetStr = i.toString(16).padStart(8, '0').toUpperCase();

      rows.push(
        <div key={i} className="flex items-center font-mono text-sm mb-1">
          {/* 偏移量 */}
          {showOffsets && (
            <div className="w-20 text-gray-500 text-right mr-4">
              {offsetStr}:
            </div>
          )}

          {/* 十六进制字节 */}
          <div className="flex-1 flex flex-wrap">
            {rowBytes.map((byte, index) => {
              const byteIndex = i + index;
              const highlight = getByteHighlight(byteIndex);

              return (
                <Tooltip key={index} title={highlight?.title}>
                  <span
                    className="px-1 mr-1 rounded cursor-pointer hover:bg-gray-200"
                    style={highlight ? {
                      backgroundColor: highlight.backgroundColor,
                      color: highlight.color
                    } : {}}
                  >
                    {byte}
                  </span>
                </Tooltip>
              );
            })}
            {/* 填充空白字节 */}
            {Array.from({ length: bytesPerRow - rowBytes.length }).map((_, index) => (
              <span key={`empty-${index}`} className="px-1 mr-1 text-gray-300">
                --
              </span>
            ))}
          </div>

          {/* ASCII 显示 */}
          {showAscii && (
            <div className="w-20 ml-4 border-l pl-2 text-gray-600">
              {rowBytes.map((byte, index) => {
                const byteIndex = i + index;
                const highlight = getByteHighlight(byteIndex);
                const ascii = byteToAscii(byte);

                return (
                  <span
                    key={index}
                    className="cursor-pointer"
                    style={highlight ? {
                      backgroundColor: highlight.backgroundColor,
                      color: highlight.color
                    } : {}}
                  >
                    {ascii}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    return <div className="bg-gray-50 p-4 rounded border">{rows}</div>;
  };

  // 处理数据变化
  const handleDataChange = (value: string) => {
    setHexData(value);
    onDataChange?.(value);
  };

  // 格式化十六进制数据
  const formatHexData = () => {
    if (!isValidHex) return;
    const formatted = cleanHexData.match(/.{1,2}/g)?.join(' ') || '';
    handleDataChange(formatted);
  };

  // 转换为文本模式
  const convertToText = () => {
    if (!isValidHex) return '';
    return hexToBytes.map(byteToAscii).join('');
  };

  // 从文本转换为十六进制
  const convertFromText = (text: string) => {
    return Array.from(text)
      .map(char => char.charCodeAt(0).toString(16).padStart(2, '0'))
      .join('')
      .toUpperCase();
  };

  // 复制到剪贴板
  const copyToClipboard = () => {
    navigator.clipboard.writeText(cleanHexData);
  };

  // 导出数据
  const exportData = () => {
    const blob = new Blob([cleanHexData], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hex_data_${new Date().getTime()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const statsInfo = [
    { label: '总字节数', value: hexToBytes.length },
    { label: '数据长度', value: `${cleanHexData.length} 字符` },
    { label: '行数', value: Math.ceil(hexToBytes.length / bytesPerRow) }
  ];

  return (
    <div className="space-y-4">
      {/* 数据输入区域 */}
      <Card
        title={title}
        extra={
          <Space>
            <Button
              size="small"
              type={showOptions ? 'primary' : 'default'}
              icon={<EyeOutlined />}
              onClick={() => setShowOptions(!showOptions)}
            >
              选项
            </Button>
            <Button size="small" onClick={formatHexData} disabled={!editable}>
              格式化
            </Button>
            <Button size="small" icon={<CopyOutlined />} onClick={copyToClipboard}>
              复制
            </Button>
            <Button size="small" icon={<ClearOutlined />} onClick={() => handleDataChange('')} disabled={!editable}>
              清空
            </Button>
            <Button size="small" icon={<DownloadOutlined />} onClick={exportData}>
              导出
            </Button>
          </Space>
        }
      >
        {/* 显示选项 */}
        {showOptions && (
          <div className="mb-4 p-3 bg-gray-50 rounded">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm">显示ASCII:</span>
                <Switch size="small" checked={showAscii} onChange={setShowAscii} />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm">显示偏移:</span>
                <Switch size="small" checked={showOffsets} onChange={setShowOffsets} />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm">输入模式:</span>
                <Button.Group size="small">
                  <Button type={inputMode === 'hex' ? 'primary' : 'default'} onClick={() => setInputMode('hex')}>
                    Hex
                  </Button>
                  <Button type={inputMode === 'text' ? 'primary' : 'default'} onClick={() => setInputMode('text')}>
                    Text
                  </Button>
                </Button.Group>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm">每行字节:</span>
                <Button.Group size="small">
                  {[8, 16, 32].map(count => (
                    <Button
                      key={count}
                      type={bytesPerRow === count ? 'primary' : 'default'}
                      onClick={() => setBytesPerRow(count)}
                    >
                      {count}
                    </Button>
                  ))}
                </Button.Group>
              </div>
            </div>
          </div>
        )}

        {/* 数据输入 */}
        {editable && (
          <div className="mb-4">
            {inputMode === 'hex' ? (
              <TextArea
                value={hexData}
                onChange={(e) => handleDataChange(e.target.value)}
                placeholder="输入十六进制数据，如: AA55 1234 ABCD..."
                rows={4}
                className="font-mono"
              />
            ) : (
              <TextArea
                value={convertToText()}
                onChange={(e) => handleDataChange(convertFromText(e.target.value))}
                placeholder="输入文本数据，将自动转换为十六进制..."
                rows={4}
              />
            )}
          </div>
        )}

        {/* 数据统计 */}
        <div className="flex gap-4 text-sm text-gray-600 mb-4">
          {statsInfo.map(({ label, value }) => (
            <div key={label}>
              <span className="text-gray-500">{label}: </span>
              <span className="font-medium">{value}</span>
            </div>
          ))}
        </div>

        {/* 高亮范围说明 */}
        {highlightRanges.length > 0 && (
          <div className="mb-4">
            <div className="text-sm text-gray-600 mb-2">字段映射:</div>
            <div className="flex flex-wrap gap-2">
              {highlightRanges.map((range, index) => (
                <Tag
                  key={index}
                  color={range.color}
                  className="text-xs"
                >
                  {range.label} ({range.start}-{range.end})
                </Tag>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* 十六进制视图 */}
      <Card title="数据视图" size="small">
        {renderHexView()}
      </Card>
    </div>
  );
}