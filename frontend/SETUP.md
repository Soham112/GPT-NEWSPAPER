# Quick Setup Guide

## ⚠️ Red Files/Errors in Your IDE?

**This is normal!** The red error indicators you're seeing are because dependencies haven't been installed yet. The code is correct, but TypeScript needs the type definitions from the installed packages.

## Fix All Errors in 2 Steps:

### Step 1: Install Dependencies
```bash
cd gpt-newspaper/frontend
npm install
```

This will install:
- React and React DOM
- Next.js
- TypeScript
- Tailwind CSS
- All type definitions (@types/node, @types/react, etc.)

### Step 2: Wait for Installation
Once `npm install` completes, all the red errors will disappear automatically. Your IDE will recognize:
- ✅ React types
- ✅ Next.js types  
- ✅ Node.js types
- ✅ JSX support

## After Installation

Run the dev server:
```bash
npm run dev
```

Then open http://localhost:3000

---

**Note:** The red files you're seeing are:
- `pages/index.tsx` - Needs React/Next.js types
- `pages/_app.tsx` - Needs Next.js types
- `tsconfig.json` - Needs @types/node

All of these will be resolved after `npm install` completes.

