import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL('https://geodisk-lab.lelewang1012.chatgpt.site'),
  title: 'GeoDisk Lab · Visual Analytics Workbench',
  description: '单屏联动的拓扑保持时空映射与诊断系统。',
  openGraph: {
    title: 'GeoDisk Lab · Topology-Aware Visual Analytics',
    description: '单屏联动的拓扑保持时空映射与诊断系统。',
    images: [{ url: '/geodisk-social-preview.png', width: 1200, height: 630 }],
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'GeoDisk Lab · Topology-Aware Visual Analytics',
    description: '单屏联动的拓扑保持时空映射与诊断系统。',
    images: ['/geodisk-social-preview.png'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
