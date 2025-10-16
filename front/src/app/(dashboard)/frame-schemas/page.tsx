import Link from 'next/link';

export default function FrameSchemasPage() {
  return (
    <div className="p-10 space-y-4">
      <h1 className="text-2xl font-semibold text-gray-900">帧格式管理入口已调整</h1>
      <p className="text-gray-600">
        帧格式的维护功能已整合到 <strong>数据源 &gt; 新建 / 编辑 UDP 数据源</strong> 的表单中，
        可在其中选择已发布的帧格式或刷新列表。
      </p>
      <p className="text-gray-600">
        若需批量导入或查看帧格式，可使用后端脚本
        <code className="mx-1 px-2 py-1 bg-gray-100 rounded text-sm">uv run python scripts/manage_frame_schemas.py</code>
        提供的 <code>list</code> / <code>import</code> 命令。
      </p>
      <Link
        href="/data-sources"
        className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-500 transition-colors"
      >
        前往数据源管理
      </Link>
    </div>
  );
}
