'use client'

import React from 'react'
import JsonView from '@uiw/react-json-view'

interface JsonViewerProps {
  data: any
  className?: string
}

export function JsonViewer({ data, className = '' }: JsonViewerProps) {
  return (
    <div className={`w-full ${className}`}>
      <JsonView
        value={data}
        style={{
          backgroundColor: 'transparent',
          fontSize: '13px',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
        }}
        displayDataTypes={false}
        displayObjectSize={false}
        collapsed={2}
        enableClipboard={true}
        highlightUpdates={false}
        indentWidth={15}
      />
    </div>
  )
}

