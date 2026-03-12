# 🎨 Component Showcase

## All Components Created

### 📁 Layout Components

#### 1. **RagDashboard** (`pages/RagDashboard.jsx`)
- Main application container
- 3-panel responsive layout
- State management for documents, messages, sources
- API integration

### 📂 Sidebar Components

#### 2. **SidebarDocuments** (`components/SidebarDocuments.jsx`)
- Document list with icons
- Select/highlight active document
- Delete functionality
- Empty state with helpful message

#### 3. **DocumentUpload** (`components/DocumentUpload.jsx`)
- Drag & drop file upload
- File preview before upload
- Progress indicator
- Success/error messages
- Supports PDF, CSV, TXT

### 💬 Chat Components

#### 4. **ChatContainer** (`components/ChatContainer.jsx`)
- Main chat interface
- Auto-scroll to latest message
- Empty state with suggestions
- Message history

#### 5. **ChatMessage** (`components/ChatMessage.jsx`)
- Individual message bubble
- User messages (right, blue)
- AI messages (left, white)
- Avatar icons
- Smooth animations

#### 6. **ChatInput** (`components/ChatInput.jsx`)
- Text input with auto-resize
- Send button with loading state
- Enter to send, Shift+Enter for new line
- Disabled state while loading

### 📚 Sources Components

#### 7. **SourcesPanel** (`components/SourcesPanel.jsx`)
- Sources sidebar container
- Empty state with icon
- Scrollable source list
- Source count display

#### 8. **SourceCard** (`components/SourceCard.jsx`)
- Individual source display
- Similarity score badge
- Expandable content preview
- Download resume button
- Color-coded similarity (green/yellow/gray)

## 🎨 Design System

### Colors
- **Primary**: Blue (#3B82F6)
- **Success**: Green
- **Warning**: Yellow
- **Error**: Red
- **Neutral**: Slate

### Typography
- **Headers**: Bold, 18-24px
- **Body**: Regular, 14px
- **Small**: 12px
- **Tiny**: 10px

### Spacing
- **Tight**: 0.5rem (8px)
- **Normal**: 1rem (16px)
- **Loose**: 1.5rem (24px)
- **Extra**: 2rem (32px)

### Shadows
- **Small**: shadow-sm
- **Medium**: shadow-md
- **Large**: shadow-lg
- **Extra**: shadow-xl

### Animations
- **Fade In**: 0.3s ease-out
- **Slide In**: 0.3s ease-out
- **Hover**: 0.2s ease

## 🔧 Utilities

### `lib/utils.js`
- `cn()` - Class name merger (clsx + tailwind-merge)
- `formatFileSize()` - Format bytes to KB/MB
- `getFileIcon()` - Get emoji icon for file type

### `services/api.js`
- `uploadDocument()` - Upload file to backend
- `searchRAG()` - Send question to RAG API
- `listDocuments()` - Get all documents
- `downloadResume()` - Get download URL
- `deleteDocument()` - Delete document

## 📱 Responsive Design

### Desktop (1024px+)
- 3-panel layout
- Sidebar: 320px
- Chat: Flexible
- Sources: 384px

### Tablet (768px - 1023px)
- 2-panel layout
- Collapsible sidebar
- Full-width chat

### Mobile (< 768px)
- Single panel
- Tabbed navigation
- Full-screen views

## 🎯 Component Props

### SidebarDocuments
```jsx
<SidebarDocuments
  documents={[]}        // Array of documents
  selectedDoc={null}    // Currently selected document
  onSelectDoc={fn}      // Callback when document selected
  onDeleteDoc={fn}      // Callback when document deleted
/>
```

### ChatContainer
```jsx
<ChatContainer
  messages={[]}         // Array of messages
  onSendMessage={fn}    // Callback when message sent
  loading={false}       // Loading state
/>
```

### SourcesPanel
```jsx
<SourcesPanel
  sources={[]}          // Array of source chunks
/>
```

## 🚀 Usage Example

```jsx
import RagDashboard from './pages/RagDashboard';

function App() {
  return <RagDashboard />;
}
```

That's it! The dashboard handles everything internally.

## ✨ Features

- ✅ Drag & drop upload
- ✅ Real-time chat
- ✅ Source citations
- ✅ Resume downloads
- ✅ Document management
- ✅ Loading states
- ✅ Error handling
- ✅ Toast notifications
- ✅ Smooth animations
- ✅ Responsive design

All components are production-ready! 🎉
