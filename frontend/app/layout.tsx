import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'GeoDisk Lab · Visual Analytics Workbench',
  description: '单屏联动的拓扑保持时空映射与诊断系统。',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
