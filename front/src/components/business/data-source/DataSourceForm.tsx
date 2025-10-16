/* eslint-disable max-lines */
'use client';

/* eslint-disable max-lines */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Button,
  Tabs,
  Alert,
  InputNumber,
  message,
  Upload,
  Radio,
  Space,
  Typography,
  Table,
  Popconfirm,
  Divider,
  Descriptions,
  Spin,
} from 'antd';
import { ReloadOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import {
  ProtocolType,
  FrameType,
  DataType,
  ByteOrder,
  ChecksumType,
  DataSource,
  FrameSchema,
  FrameFieldConfig,
  FrameChecksumConfig,
  CreateFrameSchemaDto,
} from '@/types/api';
import { apiClient } from '@/lib/api/client';
import type { ColumnsType } from 'antd/es/table';

interface DataSourceFormProps {
  open: boolean;
  onCancel: () => void;
  onSuccess?: () => void;
  dataSource?: DataSource;
}

const { Option } = Select;
const { TextArea } = Input;

const DEFAULT_HTTP_HEADERS = JSON.stringify(
  {
    'Content-Type': 'application/json',
  },
  null,
  2
);

const DEFAULT_PARSE_OPTIONS = JSON.stringify(
  {
    format: 'json',
    fields: {
      timestamp: '$.timestamp',
      value: '$.data.value',
      device_id: '$.device.id',
    },
  },
  null,
  2
);

const parseJSON = (value?: string, fallback: any = {}) => {
  if (!value) {
    return fallback;
  }
  try {
    return JSON.parse(value);
  } catch (error) {
    throw new Error('JSON 格式不正确，请检查输入内容');
  }
};

const { Dragger } = Upload;

interface FrameSchemaTemplate {
  key: string;
  label: string;
  description?: string;
  protocolType: ProtocolType;
  frameType: FrameType;
  totalLength?: number;
  fields: FrameFieldConfig[];
  checksum?: FrameChecksumConfig | null;
  defaultVersion?: string;
}

const FRAME_SCHEMA_TEMPLATES: FrameSchemaTemplate[] = [
  {
    key: 'scada_fixed',
    label: 'SCADA 固定帧 (Modbus RTU)',
    description: '固定长度，包含寄存器值与时间戳，适用于现场采集设备。',
    protocolType: ProtocolType.UDP,
    frameType: FrameType.FIXED,
    totalLength: 16,
    defaultVersion: '1.0.0',
    fields: [
      { name: 'slave_id', data_type: DataType.UINT8, offset: 0, length: 1, byte_order: ByteOrder.BIG_ENDIAN, description: '从站地址' } as FrameFieldConfig,
      { name: 'function_code', data_type: DataType.UINT8, offset: 1, length: 1, byte_order: ByteOrder.BIG_ENDIAN, description: '功能码' } as FrameFieldConfig,
      { name: 'register_address', data_type: DataType.UINT16, offset: 2, length: 2, byte_order: ByteOrder.BIG_ENDIAN, description: '寄存器地址' } as FrameFieldConfig,
      { name: 'raw_value', data_type: DataType.UINT32, offset: 4, length: 4, byte_order: ByteOrder.BIG_ENDIAN, description: '原始寄存器值' } as FrameFieldConfig,
      {
        name: 'scaled_value',
        data_type: DataType.FLOAT32,
        offset: 4,
        length: 4,
        byte_order: ByteOrder.BIG_ENDIAN,
        scale: 0.1,
        offset_value: -273.15,
        description: '缩放后的工程量',
      } as FrameFieldConfig,
      { name: 'timestamp', data_type: DataType.UINT32, offset: 8, length: 4, byte_order: ByteOrder.BIG_ENDIAN, description: '时间戳 (Unix)' } as FrameFieldConfig,
    ],
    checksum: { type: ChecksumType.CRC16, offset: 12, length: 2 },
  },
  {
    key: 'iec104_variable',
    label: 'IEC 104 变长帧',
    description: '含 APDU 长度、控制域等字段，适用于遥控类协议。',
    protocolType: ProtocolType.TCP,
    frameType: FrameType.VARIABLE,
    defaultVersion: '1.1.0',
    fields: [
      { name: 'start_byte', data_type: DataType.UINT8, offset: 0, length: 1, byte_order: ByteOrder.BIG_ENDIAN, description: '起始字节 0x68' } as FrameFieldConfig,
      { name: 'apdu_length', data_type: DataType.UINT8, offset: 1, length: 1, byte_order: ByteOrder.BIG_ENDIAN, description: 'APDU 长度' } as FrameFieldConfig,
      { name: 'control_field', data_type: DataType.UINT32, offset: 2, length: 4, byte_order: ByteOrder.LITTLE_ENDIAN, description: '控制域' } as FrameFieldConfig,
      { name: 'type_id', data_type: DataType.UINT8, offset: 6, length: 1, byte_order: ByteOrder.BIG_ENDIAN, description: '类型标识' } as FrameFieldConfig,
      { name: 'cause_of_transmission', data_type: DataType.UINT16, offset: 7, length: 2, byte_order: ByteOrder.BIG_ENDIAN, description: '传送原因' } as FrameFieldConfig,
      { name: 'asdu_address', data_type: DataType.UINT16, offset: 9, length: 2, byte_order: ByteOrder.BIG_ENDIAN, description: 'ASDU 地址' } as FrameFieldConfig,
      {
        name: 'io_address',
        data_type: DataType.UINT32,
        offset: 11,
        length: 3,
        byte_order: ByteOrder.BIG_ENDIAN,
        description: '信息对象地址',
      } as FrameFieldConfig,
      { name: 'value', data_type: DataType.FLOAT32, offset: 14, length: 4, byte_order: ByteOrder.LITTLE_ENDIAN, description: '信息体数值' } as FrameFieldConfig,
    ],
    checksum: null,
  },
  {
    key: 'syslog_delimited',
    label: 'Syslog 文本帧',
    description: '按换行分隔的日志格式，适用于 UDP Syslog 接入。',
    protocolType: ProtocolType.UDP,
    frameType: FrameType.DELIMITED,
    defaultVersion: '0.9.0',
    fields: [
      { name: 'priority', data_type: DataType.STRING, offset: 0, length: 8, byte_order: ByteOrder.BIG_ENDIAN, description: '<PRI>' } as FrameFieldConfig,
      { name: 'timestamp', data_type: DataType.STRING, offset: 8, length: 15, byte_order: ByteOrder.BIG_ENDIAN, description: '时间戳' } as FrameFieldConfig,
      { name: 'host', data_type: DataType.STRING, offset: 23, length: 32, byte_order: ByteOrder.BIG_ENDIAN, description: '主机名' } as FrameFieldConfig,
      {
        name: 'message',
        data_type: DataType.STRING,
        offset: 55,
        length: 0,
        byte_order: ByteOrder.BIG_ENDIAN,
        description: '日志内容（直至分隔符）',
      } as FrameFieldConfig,
    ],
    checksum: null,
  },
];

const cloneTemplateFields = (fields: FrameFieldConfig[]): FrameFieldConfig[] =>
  fields.map((field) => ({
    ...field,
    scale: field.scale ?? 1,
    offset_value: field.offset_value ?? 0,
  }));

const DATA_TYPE_OPTIONS = Object.values(DataType);
const BYTE_ORDER_OPTIONS = Object.values(ByteOrder);
const FRAME_TYPE_OPTIONS = Object.values(FrameType);
const CHECKSUM_TYPE_OPTIONS = Object.values(ChecksumType);

const normalizeUploadedChecksum = (checksum: any): FrameChecksumConfig | null => {
  if (!checksum || !checksum.type) {
    return null;
  }
  const typeValue = String(checksum.type).toUpperCase();
  if (typeValue === ChecksumType.NONE) {
    return null;
  }
  return {
    type: typeValue as ChecksumType,
    offset: checksum.offset ?? checksum.checksum_offset ?? 0,
    length: checksum.length ?? checksum.checksum_length ?? 0,
  };
};

const normalizeUploadedFields = (fields: any[]): FrameFieldConfig[] =>
  fields.map((field, index) => {
    const dataTypeValue = String(field.data_type ?? field.type ?? DataType.STRING).toUpperCase();
    const byteOrderValue = String(field.byte_order ?? field.endian ?? ByteOrder.BIG_ENDIAN).toUpperCase();
    const dataTypeEnum = DATA_TYPE_OPTIONS.includes(dataTypeValue as DataType)
      ? (dataTypeValue as DataType)
      : DataType.STRING;
    const byteOrderEnum = BYTE_ORDER_OPTIONS.includes(byteOrderValue as ByteOrder)
      ? (byteOrderValue as ByteOrder)
      : ByteOrder.BIG_ENDIAN;

    return {
      name: field.name ?? `field_${index + 1}`,
      data_type: dataTypeEnum,
      offset: Number(field.offset ?? 0),
      length: Number(field.length ?? 0),
      byte_order: byteOrderEnum,
      scale: field.scale ?? 1,
      offset_value: field.offset_value ?? 0,
      description: field.description ?? null,
    };
  });

export function DataSourceForm({ open, onCancel, onSuccess, dataSource }: DataSourceFormProps) {
  const [form] = Form.useForm();
  const [protocolType, setProtocolType] = useState<ProtocolType>(ProtocolType.HTTP);
  const [udpForwardMode, setUdpForwardMode] = useState<string>('listen_only');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const defaultTemplate = FRAME_SCHEMA_TEMPLATES[0];

  const [frameSchemas, setFrameSchemas] = useState<FrameSchema[]>([]);
  const [frameSchemaLoading, setFrameSchemaLoading] = useState(false);
  const [frameSchemaModalOpen, setFrameSchemaModalOpen] = useState(false);
  const [frameSchemaModalTab, setFrameSchemaModalTab] = useState<'template' | 'upload'>('template');
  const [templateForm] = Form.useForm();
  const [selectedTemplateKey, setSelectedTemplateKey] = useState<string | undefined>(defaultTemplate?.key);
  const [templateFrameType, setTemplateFrameType] = useState<FrameType>(defaultTemplate?.frameType ?? FrameType.FIXED);
  const [templateTotalLength, setTemplateTotalLength] = useState<number | undefined>(defaultTemplate?.totalLength);
  const [templateChecksum, setTemplateChecksum] = useState<FrameChecksumConfig | null>(defaultTemplate?.checksum ?? null);
  const [templateFields, setTemplateFields] = useState<FrameFieldConfig[]>(
    defaultTemplate ? cloneTemplateFields(defaultTemplate.fields) : []
  );
  const [uploadingSchema, setUploadingSchema] = useState<Record<string, any> | null>(null);
  const [uploadingSchemaFile, setUploadingSchemaFile] = useState<string | null>(null);
  const [creatingSchema, setCreatingSchema] = useState(false);
  const [schemaDetailModalOpen, setSchemaDetailModalOpen] = useState(false);
  const [schemaDetailLoading, setSchemaDetailLoading] = useState(false);
  const [viewingSchema, setViewingSchema] = useState<FrameSchema | null>(null);

  const isEditMode = Boolean(dataSource);
  const isUdpProtocol = protocolType === ProtocolType.UDP;

  const loadFrameSchemas = useCallback(async () => {
    if (!isUdpProtocol) {
      return;
    }
    try {
      setFrameSchemaLoading(true);
      const response = await apiClient.frameSchemasV2.list({
        protocol_type: ProtocolType.UDP,
        limit: 100,
      });
      if (response.success && response.data) {
        const payload = response.data as unknown as { items?: FrameSchema[] };
        const items = Array.isArray(payload?.items) ? payload.items : [];
        setFrameSchemas(items);
      } else {
        message.error(response.error || '获取帧格式列表失败');
        setFrameSchemas([]);
      }
    } catch {
      message.error('获取帧格式列表失败');
      setFrameSchemas([]);
    } finally {
      setFrameSchemaLoading(false);
    }
  }, [isUdpProtocol]);

  useEffect(() => {
    if (!open) {
      return;
    }
    setError(null);

    if (dataSource) {
      const config = dataSource.connection_config;
      const parseConfig = dataSource.parse_config;

      setProtocolType(dataSource.protocol_type as ProtocolType);

      let protocolSpecificFields: Record<string, any> = {};
      switch (dataSource.protocol_type) {
        case 'HTTP':
          protocolSpecificFields = {
            url: config.url,
            method: config.method || 'GET',
            headers: config.headers ? JSON.stringify(config.headers, null, 2) : DEFAULT_HTTP_HEADERS,
          };
          break;
        case 'UDP':
          setUdpForwardMode(config.forward_mode || 'listen_only');
          protocolSpecificFields = {
            forward_mode: config.forward_mode || 'listen_only',
            target_hosts: config.target_hosts,
            multicast_group: config.multicast_group,
            multicast_ttl: config.multicast_ttl,
          };
          break;
        case 'MQTT':
          protocolSpecificFields = {
            mqtt_topics: config.topics,
            mqtt_username: config.username,
            mqtt_password: config.password,
            mqtt_qos: config.qos || 1,
          };
          break;
        case 'WEBSOCKET':
          protocolSpecificFields = {
            ws_reconnect_interval: config.reconnect_interval || 5,
            ws_max_retries: config.max_retries || 3,
          };
          break;
        case 'TCP':
          protocolSpecificFields = {
            tcp_keep_alive: config.keep_alive ?? true,
          };
          break;
        default:
          break;
      }

      form.setFieldsValue({
        name: dataSource.name,
        description: dataSource.description,
        protocol_type: dataSource.protocol_type,
        listen_address: config.listen_address || config.host || config.broker_host || '0.0.0.0',
        listen_port: config.listen_port || config.port || config.broker_port,
        max_connections: config.max_connections,
        timeout_seconds: config.timeout_seconds,
        buffer_size: config.buffer_size,
        auto_parse: parseConfig?.auto_parse ?? true,
        frame_schema_id: parseConfig?.frame_schema_id,
        parse_options: parseConfig?.parse_options
          ? JSON.stringify(parseConfig.parse_options, null, 2)
          : '',
        is_active: dataSource.is_active,
        ...protocolSpecificFields,
      });
    } else {
      form.resetFields();
      setProtocolType(ProtocolType.HTTP);
      setUdpForwardMode('listen_only');
      setFrameSchemas([]);
    }
  }, [open, dataSource, form]);

  useEffect(() => {
    if (!open || !isUdpProtocol) {
      return;
    }
    loadFrameSchemas();
  }, [open, isUdpProtocol, loadFrameSchemas]);

  useEffect(() => {
    if (!frameSchemaModalOpen || frameSchemaModalTab !== 'template') {
      return;
    }
    const template = FRAME_SCHEMA_TEMPLATES.find((item) => item.key === selectedTemplateKey);
    if (!template) {
      templateForm.resetFields();
      setTemplateFrameType(FrameType.FIXED);
      setTemplateTotalLength(undefined);
      setTemplateChecksum(null);
      setTemplateFields([]);
      return;
    }
    templateForm.setFieldsValue({
      template_key: template.key,
      name: template.label,
      version: template.defaultVersion || '1.0.0',
      description: template.description,
    });
    setTemplateFrameType(template.frameType);
    setTemplateTotalLength(template.totalLength ?? undefined);
    setTemplateChecksum(template.checksum ? { ...template.checksum } : null);
    setTemplateFields(cloneTemplateFields(template.fields));
  }, [frameSchemaModalOpen, frameSchemaModalTab, selectedTemplateKey, templateForm]);

  useEffect(() => {
    if (!open || !isUdpProtocol) {
      return;
    }
    const schemaId = dataSource?.parse_config?.frame_schema_id;
    if (!schemaId) {
      return;
    }
    if (frameSchemas.some((item) => item.id === schemaId)) {
      return;
    }
    (async () => {
      try {
        const resp = await apiClient.frameSchemasV2.get(schemaId);
        if (resp.success && resp.data) {
          setFrameSchemas((prev) => {
            if (prev.some((item) => item.id === schemaId)) {
              return prev;
            }
            return [...prev, resp.data as FrameSchema];
          });
        }
      } catch {
        // ignore
      }
    })();
  }, [open, isUdpProtocol, dataSource?.parse_config?.frame_schema_id, frameSchemas]);

  const handleFieldChange = useCallback(
    (index: number, key: keyof FrameFieldConfig, value: any) => {
      setTemplateFields((prev) =>
        prev.map((field, idx) => {
          if (idx !== index) {
            return field;
          }
          const next: FrameFieldConfig = { ...field };
          switch (key) {
            case 'offset':
            case 'length':
              next[key] = Number(value ?? 0);
              break;
            case 'scale':
              next.scale = value === null || value === undefined ? undefined : Number(value);
              break;
            case 'offset_value':
              next.offset_value = value === null || value === undefined ? undefined : Number(value);
              break;
            case 'data_type':
              next.data_type = value as DataType;
              break;
            case 'byte_order':
              next.byte_order = value as ByteOrder;
              break;
            default:
              (next as any)[key] = value;
          }
          return next;
        })
      );
    },
    []
  );

  const handleAddField = useCallback(() => {
    setTemplateFields((prev) => {
      const last = prev[prev.length - 1];
      const nextOffset = last ? last.offset + (last.length ?? 0) : 0;
      return [
        ...prev,
        {
          name: `field_${prev.length + 1}`,
          data_type: DataType.UINT8,
          offset: nextOffset,
          length: 1,
          byte_order: ByteOrder.BIG_ENDIAN,
          scale: 1,
          offset_value: 0,
          description: '',
        },
      ];
    });
  }, []);

  const handleRemoveField = useCallback((index: number) => {
    setTemplateFields((prev) => prev.filter((_, idx) => idx !== index));
  }, []);

  const handleDeleteSelectedFrameSchema = useCallback(async () => {
    const schemaId: string | undefined = form.getFieldValue('frame_schema_id');
    if (!schemaId) {
      message.warning('请先选择需要删除的帧格式');
      return;
    }
    const targetSchema = frameSchemas.find((item) => item.id === schemaId);
    try {
      const resp = await apiClient.frameSchemasV2.delete(schemaId);
      if (resp.success) {
        message.success(`帧格式「${targetSchema?.name ?? schemaId}」已删除`);
        form.setFieldsValue({ frame_schema_id: null });
        setFrameSchemas((prev) => prev.filter((item) => item.id !== schemaId));
        await loadFrameSchemas();
      } else {
        message.error(resp.error || '帧格式删除失败');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '帧格式删除失败';
      message.error(msg);
    }
  }, [form, frameSchemas, loadFrameSchemas]);

  const handleViewSelectedFrameSchema = useCallback(async () => {
    const schemaId: string | undefined = form.getFieldValue('frame_schema_id');
    if (!schemaId) {
      message.warning('请先选择需要查看的帧格式');
      return;
    }
    try {
      setSchemaDetailLoading(true);
      const resp = await apiClient.frameSchemasV2.get(schemaId);
      if (resp.success && resp.data) {
        setViewingSchema(resp.data as FrameSchema);
        setSchemaDetailModalOpen(true);
      } else {
        message.error(resp.error || '获取帧格式详情失败');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '获取帧格式详情失败';
      message.error(msg);
    } finally {
      setSchemaDetailLoading(false);
    }
  }, [form]);

  const checksumType = templateChecksum?.type ?? ChecksumType.NONE;

  const templateFieldColumns = useMemo<ColumnsType<FrameFieldConfig>>(() => {
    return [
      {
        title: '字段名称',
        dataIndex: 'name',
        width: 150,
        render: (_value, record, index) => {
          if (typeof index !== 'number') {
            return null;
          }
          return (
            <Input
              value={record.name}
              onChange={(event) => handleFieldChange(index, 'name', event.target.value)}
            />
          );
        },
      },
      {
        title: '数据类型',
        dataIndex: 'data_type',
        width: 140,
        render: (_value, record, index) => {
          if (typeof index !== 'number') {
            return null;
          }
          return (
            <Select
              value={record.data_type}
              onChange={(val) => handleFieldChange(index, 'data_type', val as DataType)}
              style={{ width: '100%' }}
            >
              {DATA_TYPE_OPTIONS.map((option) => (
                <Option value={option} key={option}>
                  {option}
                </Option>
              ))}
            </Select>
          );
        },
      },
      {
        title: '偏移 (字节)',
        dataIndex: 'offset',
        width: 140,
        render: (_value, record, index) => {
          if (typeof index !== 'number') {
            return null;
          }
          return (
            <InputNumber
              min={0}
              value={record.offset}
              onChange={(val) => handleFieldChange(index, 'offset', val ?? 0)}
              style={{ width: '100%' }}
            />
          );
        },
      },
      {
        title: '长度 (字节)',
        dataIndex: 'length',
        width: 140,
        render: (_value, record, index) => {
          if (typeof index !== 'number') {
            return null;
          }
          return (
            <InputNumber
              min={0}
              value={record.length}
              onChange={(val) => handleFieldChange(index, 'length', val ?? 0)}
              style={{ width: '100%' }}
            />
          );
        },
      },
      {
        title: '字节序',
        dataIndex: 'byte_order',
        width: 140,
        render: (_value, record, index) => {
          if (typeof index !== 'number') {
            return null;
          }
          return (
            <Select
              value={record.byte_order}
              onChange={(val) => handleFieldChange(index, 'byte_order', val as ByteOrder)}
              style={{ width: '100%' }}
            >
              {BYTE_ORDER_OPTIONS.map((option) => (
                <Option value={option} key={option}>
                  {option}
                </Option>
              ))}
            </Select>
          );
        },
      },
      {
        title: '缩放因子',
        dataIndex: 'scale',
        width: 130,
        render: (_value, record, index) => {
          if (typeof index !== 'number') {
            return null;
          }
          return (
            <InputNumber
              step={0.1}
              value={record.scale}
              onChange={(val) => handleFieldChange(index, 'scale', val ?? undefined)}
              style={{ width: '100%' }}
            />
          );
        },
      },
      {
        title: '偏移值',
        dataIndex: 'offset_value',
        width: 130,
        render: (_value, record, index) => {
          if (typeof index !== 'number') {
            return null;
          }
          return (
            <InputNumber
              step={0.1}
              value={record.offset_value}
              onChange={(val) => handleFieldChange(index, 'offset_value', val ?? undefined)}
              style={{ width: '100%' }}
            />
          );
        },
      },
      {
        title: '描述',
        dataIndex: 'description',
        render: (_value, record, index) => {
          if (typeof index !== 'number') {
            return null;
          }
          return (
            <Input
              value={record.description ?? ''}
              onChange={(event) => handleFieldChange(index, 'description', event.target.value)}
            />
          );
        },
      },
      {
        title: '操作',
        dataIndex: 'actions',
        width: 90,
        render: (_value, _record, index) => {
          if (typeof index !== 'number') {
            return null;
          }
          const disabled = templateFields.length <= 1;
          return (
            <Popconfirm
              title="确认删除该字段？"
              okText="删除"
              cancelText="取消"
              disabled={disabled}
              onConfirm={() => handleRemoveField(index)}
            >
              <Button
                type="text"
                size="small"
                icon={<DeleteOutlined />}
                danger
                disabled={disabled}
              />
            </Popconfirm>
          );
        },
      },
    ];
  }, [handleFieldChange, handleRemoveField, templateFields.length]);

  const renderUdpConfig = useCallback(() => {
    return (
      <>
        <Form.Item
          name="forward_mode"
          label="转发模式"
          initialValue="listen_only"
          rules={[{ required: true, message: '请选择转发模式' }]}
        >
          <Select onChange={setUdpForwardMode}>
            <Option value="listen_only">仅监听</Option>
            <Option value="unicast">单播转发</Option>
            <Option value="multicast">组播转发</Option>
          </Select>
        </Form.Item>

        {udpForwardMode === 'unicast' && (
          <Form.Item
            name="target_hosts"
            label="目标主机列表"
            rules={[{ required: true, message: '请输入目标主机，格式 host:port,host2:port2' }]}
          >
            <Input placeholder="192.168.1.100:9001,192.168.1.101:9001" />
          </Form.Item>
        )}

        {udpForwardMode === 'multicast' && (
          <>
            <Form.Item
              name="multicast_group"
              label="组播地址"
              rules={[{ required: true, message: '请输入组播地址' }]}
            >
              <Input placeholder="239.0.0.1" />
            </Form.Item>
            <Form.Item
              name="multicast_ttl"
              label="TTL"
              initialValue={1}
            >
              <InputNumber min={1} max={255} style={{ width: '100%' }} />
            </Form.Item>
          </>
        )}

        <Form.Item
          name="frame_schema_id"
          label="帧格式（可选）"
          tooltip="选择已发布的帧格式以解析 UDP 数据帧"
        >
          <Select
            allowClear
            placeholder="选择帧格式"
            loading={frameSchemaLoading}
            onDropdownVisibleChange={(visible) => {
              if (visible) {
                loadFrameSchemas();
              }
            }}
            options={frameSchemas.map((schema) => ({
              label: `${schema.name} v${schema.version}`,
              value: schema.id,
            }))}
          />
        </Form.Item>
        <Button
          type="link"
          icon={<ReloadOutlined />}
          onClick={loadFrameSchemas}
          style={{ paddingLeft: 0 }}
        >
          刷新帧格式列表
        </Button>
        <Button
          type="link"
          onClick={() => {
            setFrameSchemaModalTab('template');
            setFrameSchemaModalOpen(true);
          }}
        >
          新建帧格式
        </Button>
        <Button
          type="link"
          onClick={handleViewSelectedFrameSchema}
        >
          查看帧格式详情
        </Button>
        <Button
          type="link"
          danger
          onClick={handleDeleteSelectedFrameSchema}
        >
          删除所选帧格式
        </Button>
      </>
    );
  }, [
    frameSchemaLoading,
    frameSchemas,
    loadFrameSchemas,
    udpForwardMode,
    form,
    handleDeleteSelectedFrameSchema,
    handleViewSelectedFrameSchema,
  ]);

  const renderConnectionConfig = useCallback(() => {
    switch (protocolType) {
      case ProtocolType.HTTP:
        return (
          <>
            <Form.Item
              name="url"
              label="HTTP URL"
              rules={[{ required: true, message: '请输入 HTTP URL' }]}
            >
              <Input placeholder="https://api.example.com/data" />
            </Form.Item>
            <Form.Item
              name="method"
              label="请求方法"
              initialValue="GET"
            >
              <Select>
                <Option value="GET">GET</Option>
                <Option value="POST">POST</Option>
                <Option value="PUT">PUT</Option>
                <Option value="PATCH">PATCH</Option>
              </Select>
            </Form.Item>
            <Form.Item
              name="headers"
              label="HTTP Headers (JSON)"
              initialValue={DEFAULT_HTTP_HEADERS}
            >
              <TextArea rows={4} placeholder={DEFAULT_HTTP_HEADERS} />
            </Form.Item>
          </>
        );
      case ProtocolType.UDP:
        return renderUdpConfig();
      case ProtocolType.MQTT:
        return (
          <>
            <Form.Item
              name="mqtt_topics"
              label="订阅主题"
              rules={[{ required: true, message: '请输入订阅主题' }]}
            >
              <Input placeholder="sensors/+/temperature" />
            </Form.Item>
            <Form.Item name="mqtt_username" label="用户名">
              <Input placeholder="MQTT 用户名" />
            </Form.Item>
            <Form.Item name="mqtt_password" label="密码">
              <Input placeholder="MQTT 密码" />
            </Form.Item>
            <Form.Item name="mqtt_qos" label="QoS" initialValue={1}>
              <InputNumber min={0} max={2} style={{ width: '100%' }} />
            </Form.Item>
          </>
        );
      case ProtocolType.WEBSOCKET:
        return (
          <>
            <Form.Item
              name="ws_reconnect_interval"
              label="重连间隔 (秒)"
              initialValue={5}
            >
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="ws_max_retries"
              label="最大重试次数"
              initialValue={3}
            >
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </>
        );
      case ProtocolType.TCP:
        return (
          <Form.Item
            name="tcp_keep_alive"
            label="保持长连接"
            valuePropName="checked"
            initialValue
          >
            <Switch />
          </Form.Item>
        );
      default:
        return null;
    }
  }, [protocolType, renderUdpConfig]);

  const parsingTab = useMemo(() => {
    return (
      <>
        <Form.Item
          name="auto_parse"
          label="自动解析"
          initialValue
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
        <Form.Item
          name="parse_options"
          label="解析选项 (JSON)"
          help="定义额外的解析选项，留空使用默认配置"
        >
          <TextArea rows={6} placeholder={DEFAULT_PARSE_OPTIONS} />
        </Form.Item>
      </>
    );
  }, []);

  const handleSubmit = async (values: Record<string, any>) => {
    try {
      setLoading(true);
      setError(null);

      const connection_config: Record<string, any> = {
        listen_address: values.listen_address || '0.0.0.0',
        listen_port: values.listen_port,
        max_connections: values.max_connections,
        timeout_seconds: values.timeout_seconds,
        buffer_size: values.buffer_size,
      };

      switch (protocolType) {
        case ProtocolType.HTTP:
          connection_config.url = values.url;
          connection_config.method = values.method || 'GET';
          connection_config.headers = parseJSON(values.headers, {});
          break;
        case ProtocolType.UDP:
          connection_config.forward_mode = values.forward_mode || 'listen_only';
          if (values.forward_mode === 'unicast') {
            connection_config.target_hosts = values.target_hosts;
          } else if (values.forward_mode === 'multicast') {
            connection_config.multicast_group = values.multicast_group;
            connection_config.multicast_ttl = values.multicast_ttl;
          }
          break;
        case ProtocolType.MQTT:
          connection_config.topics = values.mqtt_topics;
          connection_config.username = values.mqtt_username;
          connection_config.password = values.mqtt_password;
          connection_config.qos = values.mqtt_qos || 1;
          break;
        case ProtocolType.WEBSOCKET:
          connection_config.reconnect_interval = values.ws_reconnect_interval || 5;
          connection_config.max_retries = values.ws_max_retries || 3;
          break;
        case ProtocolType.TCP:
          connection_config.keep_alive = values.tcp_keep_alive ?? true;
          break;
        default:
          break;
      }

      const parse_config: Record<string, any> = {
        auto_parse: values.auto_parse ?? true,
        frame_schema_id: values.frame_schema_id || null,
        parse_options: parseJSON(values.parse_options, {}),
      };

      const payload = {
        name: values.name,
        description: values.description || null,
        protocol_type: protocolType,
        connection_config,
        parse_config,
        is_active: values.is_active ?? true,
      };

      let response;
      if (isEditMode && dataSource) {
        response = await apiClient.dataSourcesV2.update(dataSource.id, payload);
      } else {
        response = await apiClient.dataSourcesV2.create(payload);
      }

      if (response.success) {
        form.resetFields();
        onSuccess?.();
        onCancel();
      } else {
        const msg = response.error || (isEditMode ? '更新失败' : '创建失败');
        setError(msg);
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(isEditMode ? '更新失败' : '创建失败');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSchemaFromTemplate = async (values: Record<string, any>) => {
    try {
      setCreatingSchema(true);
      const template = FRAME_SCHEMA_TEMPLATES.find((item) => item.key === values.template_key);
      if (!template) {
        throw new Error('请选择模板');
      }
      if (!templateFields.length) {
        throw new Error('请至少保留一个字段定义');
      }

      if (templateFrameType === FrameType.FIXED && (!templateTotalLength || templateTotalLength <= 0)) {
        throw new Error('固定长度帧需要设置总长度');
      }

      const normalizedFields: FrameFieldConfig[] = templateFields.map((field) => ({
        ...field,
        scale: field.scale ?? 1,
        offset_value: field.offset_value ?? 0,
      }));

      const checksumPayload =
        templateChecksum && templateChecksum.type !== ChecksumType.NONE
          ? { ...templateChecksum }
          : undefined;

      const payload: CreateFrameSchemaDto = {
        name: values.name,
        description: values.description,
        version: values.version,
        protocol_type: template.protocolType,
        frame_type: templateFrameType,
        total_length:
          templateFrameType === FrameType.FIXED ? templateTotalLength ?? undefined : templateTotalLength ?? undefined,
        fields: normalizedFields,
        checksum: checksumPayload,
        is_published: true,
      };

      const response = await apiClient.frameSchemasV2.create(payload);
      if (!response.success || !response.data) {
        throw new Error(response.error || '创建帧格式失败');
      }
      const created = response.data as FrameSchema;
      await loadFrameSchemas();
      form.setFieldsValue({ frame_schema_id: created.id });
      setFrameSchemaModalOpen(false);
      templateForm.resetFields();
      setSelectedTemplateKey(FRAME_SCHEMA_TEMPLATES[0]?.key);
      message.success(`帧格式 ${created.name} 已创建`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '创建帧格式失败';
      message.error(msg);
    } finally {
      setCreatingSchema(false);
    }
  };

  const handleCreateSchemaFromUpload = async () => {
    if (!uploadingSchema) {
      message.error('请先上传帧格式 JSON 文件');
      return;
    }
    try {
      setCreatingSchema(true);
      const {
        name,
        description,
        version,
        protocol_type,
        frame_type,
        total_length,
        fields,
        checksum,
        is_published,
      } = uploadingSchema as Record<string, any>;

      const normalizedFields = normalizeUploadedFields(Array.isArray(fields) ? fields : []);
      if (!normalizedFields.length) {
        throw new Error('帧格式字段定义不能为空');
      }

      const protocolValue =
        typeof protocol_type === 'string'
          ? (protocol_type as string).toUpperCase()
          : protocol_type ?? ProtocolType.UDP;
      const frameTypeValue =
        typeof frame_type === 'string'
          ? (frame_type as string).toUpperCase()
          : frame_type ?? FrameType.FIXED;

      const normalizedProtocol = Object.values(ProtocolType).includes(protocolValue as ProtocolType)
        ? (protocolValue as ProtocolType)
        : ProtocolType.UDP;
      const normalizedFrameType = Object.values(FrameType).includes(frameTypeValue as FrameType)
        ? (frameTypeValue as FrameType)
        : FrameType.FIXED;

      const checksumConfig = normalizeUploadedChecksum(checksum);

      const numericTotalLength =
        total_length === undefined || total_length === null ? undefined : Number(total_length);

      const payload: CreateFrameSchemaDto = {
        name,
        description,
        version,
        protocol_type: normalizedProtocol,
        frame_type: normalizedFrameType,
        total_length: numericTotalLength,
        fields: normalizedFields,
        checksum: checksumConfig ?? undefined,
        is_published: is_published ?? true,
      };
      const response = await apiClient.frameSchemasV2.create(payload);
      if (!response.success || !response.data) {
        throw new Error(response.error || '创建帧格式失败');
      }
      const created = response.data as FrameSchema;
      await loadFrameSchemas();
      form.setFieldsValue({ frame_schema_id: created.id });
      setFrameSchemaModalOpen(false);
      setUploadingSchema(null);
      setUploadingSchemaFile(null);
      message.success(`帧格式 ${created.name} 已创建`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '创建帧格式失败';
      message.error(msg);
    } finally {
      setCreatingSchema(false);
    }
  };

  return (
    <Modal
      destroyOnClose
      title={isEditMode ? '编辑数据源' : '创建数据源'}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={860}
    >
      {error && (
        <Alert
          message={isEditMode ? '更新失败' : '创建失败'}
          description={error}
          type="error"
          closable
          onClose={() => setError(null)}
          className="mb-4"
        />
      )}

      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item
          name="name"
          label="数据源名称"
          rules={[{ required: true, message: '请输入数据源名称' }]}
        >
          <Input placeholder="输入数据源名称" />
        </Form.Item>

        <Form.Item name="description" label="描述">
          <TextArea rows={2} placeholder="输入数据源描述" />
        </Form.Item>

        <Form.Item label="协议类型">
          <Select
            value={protocolType}
            onChange={(value) => {
              const next = value as ProtocolType;
              setProtocolType(next);
              if (next === ProtocolType.UDP) {
                const currentMode = form.getFieldValue('forward_mode') || 'listen_only';
                setUdpForwardMode(currentMode);
                loadFrameSchemas();
              } else {
                setUdpForwardMode('listen_only');
                form.setFieldsValue({ frame_schema_id: null });
              }
            }}
            disabled={isEditMode}
          >
            <Option value={ProtocolType.HTTP}>HTTP</Option>
            <Option value={ProtocolType.UDP}>UDP</Option>
            <Option value={ProtocolType.MQTT}>MQTT</Option>
            <Option value={ProtocolType.WEBSOCKET}>WebSocket</Option>
            <Option value={ProtocolType.TCP}>TCP</Option>
          </Select>
        </Form.Item>

        <Tabs
          defaultActiveKey="connection"
          items={[
            {
              key: 'connection',
              label: '连接配置',
              children: (
                <>
                  <Form.Item
                    name="listen_address"
                    label="监听地址"
                    initialValue="0.0.0.0"
                    rules={[{ required: true, message: '请输入监听地址' }]}
                  >
                    <Input placeholder="0.0.0.0" />
                  </Form.Item>
                  <Form.Item
                    name="listen_port"
                    label="监听端口"
                    rules={[{ required: true, message: '请输入端口号' }]}
                  >
                    <InputNumber min={1} max={65535} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item name="max_connections" label="最大连接数">
                    <InputNumber min={1} max={10000} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item name="timeout_seconds" label="超时时间 (秒)">
                    <InputNumber min={1} max={600} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item name="buffer_size" label="缓冲区大小 (字节)">
                    <InputNumber min={256} max={65535} step={256} style={{ width: '100%' }} />
                  </Form.Item>
                  {renderConnectionConfig()}
                </>
              ),
            },
            {
              key: 'parsing',
              label: '数据解析',
              children: parsingTab,
            },
          ]}
        />

        <Form.Item
          name="is_active"
          label="启用状态"
          initialValue
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>

        <Form.Item className="mb-0 text-right">
          <Button onClick={onCancel} className="mr-2">
            取消
          </Button>
          <Button type="primary" htmlType="submit" loading={loading} disabled={loading}>
          {isEditMode ? '保存' : '创建'}
        </Button>
      </Form.Item>
      </Form>

      <Modal
        title={viewingSchema ? `帧格式详情 - ${viewingSchema.name}` : '帧格式详情'}
        open={schemaDetailModalOpen}
        onCancel={() => {
          setSchemaDetailModalOpen(false);
          setViewingSchema(null);
        }}
        footer={null}
        width={720}
        destroyOnClose
      >
        {schemaDetailLoading ? (
          <div className="flex justify-center py-8"><Spin /></div>
        ) : viewingSchema ? (
          <div className="space-y-4">
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="名称">{viewingSchema.name}</Descriptions.Item>
              <Descriptions.Item label="版本">{viewingSchema.version}</Descriptions.Item>
              <Descriptions.Item label="协议类型">{viewingSchema.protocol_type}</Descriptions.Item>
              <Descriptions.Item label="帧类型">{viewingSchema.frame_type}</Descriptions.Item>
              <Descriptions.Item label="总长度" span={2}>
                {viewingSchema.total_length ?? '未指定'}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {viewingSchema.description ?? '—'}
              </Descriptions.Item>
              <Descriptions.Item label="校验" span={2}>
                {viewingSchema.checksum
                  ? `${viewingSchema.checksum.type} (offset=${viewingSchema.checksum.offset ?? 0}, length=${viewingSchema.checksum.length ?? 0})`
                  : 'NONE'}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {new Date(viewingSchema.created_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间" span={2}>
                {new Date(viewingSchema.updated_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            </Descriptions>
            <div>
              <Typography.Title level={5}>字段定义</Typography.Title>
              <pre className="bg-gray-100 rounded p-3 text-xs overflow-auto" style={{ maxHeight: 280 }}>
{JSON.stringify(viewingSchema.fields, null, 2)}
              </pre>
            </div>
          </div>
        ) : (
          <Alert type="info" message="未加载到帧格式详情" showIcon />
        )}
      </Modal>

      <Modal
        title="创建帧格式"
        open={frameSchemaModalOpen}
        onCancel={() => {
          setFrameSchemaModalOpen(false);
          setFrameSchemaModalTab('template');
          setSelectedTemplateKey(FRAME_SCHEMA_TEMPLATES[0]?.key);
          templateForm.resetFields();
          setUploadingSchema(null);
          setUploadingSchemaFile(null);
          if (defaultTemplate) {
            setTemplateFrameType(defaultTemplate.frameType);
            setTemplateTotalLength(defaultTemplate.totalLength ?? undefined);
            setTemplateChecksum(defaultTemplate.checksum ? { ...defaultTemplate.checksum } : null);
            setTemplateFields(cloneTemplateFields(defaultTemplate.fields));
          } else {
            setTemplateFrameType(FrameType.FIXED);
            setTemplateTotalLength(undefined);
            setTemplateChecksum(null);
            setTemplateFields([]);
          }
        }}
        footer={null}
        width={640}
        destroyOnClose
      >
        <Tabs
          activeKey={frameSchemaModalTab}
          onChange={(key) => setFrameSchemaModalTab(key as 'template' | 'upload')}
          items={[
            {
              key: 'template',
              label: '使用模板',
              children: (
                <Form form={templateForm} layout="vertical" onFinish={handleCreateSchemaFromTemplate}>
                  <Form.Item
                    name="template_key"
                    label="选择模板"
                    initialValue={FRAME_SCHEMA_TEMPLATES[0]?.key}
                    rules={[{ required: true, message: '请选择模板' }]}
                  >
                    <Radio.Group
                      value={selectedTemplateKey}
                      onChange={(event) => {
                        setSelectedTemplateKey(event.target.value);
                        templateForm.setFieldsValue({ template_key: event.target.value });
                      }}
                      className="w-full"
                    >
                      <Space direction="vertical" className="w-full">
                        {FRAME_SCHEMA_TEMPLATES.map((item) => (
                          <Radio value={item.key} key={item.key} className="w-full">
                            <span className="font-medium">{item.label}</span>
                            {item.description && (
                              <Typography.Text type="secondary" className="block text-xs">
                                {item.description}
                              </Typography.Text>
                            )}
                          </Radio>
                        ))}
                      </Space>
                    </Radio.Group>
                  </Form.Item>
                  <Form.Item
                    name="name"
                    label="帧格式名称"
                    rules={[{ required: true, message: '请输入帧格式名称' }]}
                  >
                    <Input placeholder="例如：SCADA Fixed Frame" />
                  </Form.Item>
                  <Form.Item name="description" label="描述">
                    <TextArea rows={2} placeholder="帧格式描述" />
                  </Form.Item>
                  <Form.Item
                    name="version"
                    label="版本号"
                    rules={[{ required: true, message: '请输入版本号' }]}
                  >
                    <Input placeholder="1.0.0" />
                  </Form.Item>
                  <Divider />
                  <Typography.Paragraph strong>帧结构设置</Typography.Paragraph>
                  <Form.Item label="帧类型">
                    <Select
                      value={templateFrameType}
                      onChange={(val) => setTemplateFrameType(val as FrameType)}
                    >
                      {FRAME_TYPE_OPTIONS.map((option) => (
                        <Option value={option} key={option}>
                          {option}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                  <Form.Item label="总长度 (字节)" extra="仅固定帧需要填写">
                    <InputNumber
                      min={1}
                      style={{ width: '100%' }}
                      value={templateTotalLength}
                      disabled={templateFrameType !== FrameType.FIXED}
                      onChange={(val) => setTemplateTotalLength(val ?? undefined)}
                    />
                  </Form.Item>
                  <Form.Item label="校验类型">
                    <Select
                      value={checksumType}
                      onChange={(val) => {
                        if (val === ChecksumType.NONE) {
                          setTemplateChecksum(null);
                        } else {
                          setTemplateChecksum((prev) => ({
                            type: val as ChecksumType,
                            offset: prev?.offset ?? 0,
                            length: prev?.length ?? 0,
                          }));
                        }
                      }}
                    >
                      {CHECKSUM_TYPE_OPTIONS.map((option) => (
                        <Option value={option} key={option}>
                          {option}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                  {checksumType !== ChecksumType.NONE && (
                    <Space size="large" className="w-full">
                      <div className="flex-1">
                        <Typography.Text type="secondary">偏移</Typography.Text>
                        <InputNumber
                          min={0}
                          style={{ width: '100%' }}
                          value={templateChecksum?.offset ?? 0}
                          onChange={(val) =>
                            setTemplateChecksum((prev) => ({
                              type: (prev?.type ?? checksumType) as ChecksumType,
                              offset: Number(val ?? 0),
                              length: prev?.length ?? 0,
                            }))
                          }
                        />
                      </div>
                      <div className="flex-1">
                        <Typography.Text type="secondary">长度</Typography.Text>
                        <InputNumber
                          min={1}
                          style={{ width: '100%' }}
                          value={templateChecksum?.length ?? 0}
                          onChange={(val) =>
                            setTemplateChecksum((prev) => ({
                              type: (prev?.type ?? checksumType) as ChecksumType,
                              offset: prev?.offset ?? 0,
                              length: Number(val ?? 0),
                            }))
                          }
                        />
                      </div>
                    </Space>
                  )}

                  <Divider />
                  <Typography.Paragraph strong>字段列表</Typography.Paragraph>
                  <Table
                    columns={templateFieldColumns}
                    dataSource={templateFields}
                    pagination={false}
                    size="small"
                    rowKey={(_, index) => index?.toString() ?? 'field'}
                    scroll={{ x: 'max-content' }}
                  />
                  <Button
                    className="mt-3"
                    type="dashed"
                    icon={<PlusOutlined />}
                    onClick={handleAddField}
                    block
                  >
                    新增字段
                  </Button>

                  <div className="text-right mt-4">
                    <Button htmlType="submit" type="primary" loading={creatingSchema}>
                      创建并使用
                    </Button>
                  </div>
                </Form>
              ),
            },
            {
              key: 'upload',
              label: '上传 JSON',
              children: (
                <>
                  <Dragger
                    multiple={false}
                    showUploadList={false}
                    beforeUpload={(file) => {
                      const reader = new FileReader();
                      reader.onload = () => {
                        try {
                          const text = reader.result as string;
                          const parsed = JSON.parse(text);
                          if (Array.isArray(parsed)) {
                            if (!parsed.length) {
                              throw new Error('JSON 内容为空');
                            }
                            setUploadingSchema(parsed[0]);
                          } else {
                            setUploadingSchema(parsed);
                          }
                          setUploadingSchemaFile(file.name);
                          message.success('JSON 解析成功，可点击“创建并使用”');
                        } catch (err) {
                          const msg = err instanceof Error ? err.message : 'JSON 解析失败';
                          setUploadingSchema(null);
                          setUploadingSchemaFile(null);
                          message.error(msg);
                        }
                      };
                      reader.readAsText(file);
                      return false;
                    }}
                  >
                    <p className="ant-upload-drag-icon">
                      <ReloadOutlined />
                    </p>
                    <p className="ant-upload-text">拖拽或点击上传帧格式 JSON 文件</p>
                    <p className="ant-upload-hint">支持单个对象或对象数组，默认读取第一条记录</p>
                  </Dragger>
                  {uploadingSchemaFile && (
                    <Alert
                      className="mt-3"
                      type="success"
                      message={`已加载文件：${uploadingSchemaFile}`}
                      showIcon
                    />
                  )}
                  <div className="mt-4 text-right">
                    <Button type="primary" onClick={handleCreateSchemaFromUpload} loading={creatingSchema}>
                      创建并使用
                    </Button>
                  </div>
                </>
              ),
            },
          ]}
        />
      </Modal>
    </Modal>
  );
}
