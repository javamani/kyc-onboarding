@echo off
echo ==========================================
echo Creating React App + Tailwind Setup
echo ==========================================

cd /d C:\HappyLearnings\workspace-gen-ai\kyc-onboarding

echo.
echo Step 1: Creating React App...
npx create-react-app@latest new-frontend

cd new-frontend

echo.
echo Step 2: Installing Tailwind + PostCSS...
npm install -D tailwindcss @tailwindcss/postcss postcss autoprefixer

echo.
echo Step 3: Creating Tailwind config...
(
echo /** @type {import('tailwindcss').Config} */
echo module.exports = {
echo   content: ["./src/**/*.{js,jsx,ts,tsx}"],
echo   theme: { extend: {} },
echo   plugins: [],
echo };
) > tailwind.config.js

echo.
echo Step 4: Creating PostCSS config...
(
echo module.exports = {
echo   plugins: {
echo     "@tailwindcss/postcss": {},
echo     autoprefixer: {},
echo   },
echo };
) > postcss.config.js

echo.
echo Step 5: Updating index.css...
(
echo @tailwind base;
echo @tailwind components;
echo @tailwind utilities;
) > src\index.css

echo.
echo Step 6: Updating App.js for test UI...
(
echo export default function App() {
echo   return (
echo     ^<div className="flex items-center justify-center h-screen bg-slate-100"^>
echo       ^<h1 className="text-4xl font-bold text-green-600"^>
echo         KYC Onboarding UI Ready 🚀
echo       ^</h1^>
echo     ^</div^>
echo   );
echo }
) > src\App.js

echo.
echo ==========================================
echo ✅ Setup Complete!
echo Run the app with:
echo cd new-frontend
echo npm start
echo ==========================================
pause
