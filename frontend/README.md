# XLR8 Research - Next.js Frontend

This is the Next.js + React + Tailwind frontend for XLR8 Research, refactored to have a ChatGPT-like interface.

## Setup

**⚠️ IMPORTANT: You must install dependencies first to resolve TypeScript errors!**

1. **Install dependencies** (this will resolve all the red error indicators):
```bash
cd gpt-newspaper/frontend
npm install
# or
yarn install
```

After running `npm install`, all TypeScript errors will disappear as the type definitions for React, Next.js, and Node.js will be available.

2. Create a `.env.local` file (optional, defaults to localhost:8000):
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

3. Run the development server:
```bash
npm run dev
# or
yarn dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Troubleshooting

**Red files/errors in IDE?**
- These are expected until you run `npm install`
- All errors will resolve once dependencies are installed
- The code itself is correct, it just needs the type definitions

## Features

- **ChatGPT-like Interface**: Full-height chat layout with centered messages
- **Dynamic Header**: "XLR8 Research" title and "Outreach Agent" button only show before first response
- **Message History**: User prompts and assistant responses in a scrollable chat format
- **Result Cards**: Research results rendered as assistant messages with full content
- **Typography**: 15px base font size with relaxed line height, system font stack
- **Responsive**: Works on mobile and desktop

## Project Structure

```
frontend/
├── pages/
│   ├── _app.tsx          # Next.js app wrapper
│   └── index.tsx          # Main chat interface
├── styles/
│   └── globals.css        # Global styles with Tailwind
├── tailwind.config.js     # Tailwind configuration
├── next.config.js         # Next.js configuration
├── tsconfig.json          # TypeScript configuration
└── package.json           # Dependencies
```

## Key Changes from Vanilla HTML/JS

- Converted to React components with TypeScript
- Implemented message state management
- Added ChatGPT-like chat interface
- Integrated Tailwind CSS for styling
- Maintained all existing functionality (API calls, result rendering, etc.)

