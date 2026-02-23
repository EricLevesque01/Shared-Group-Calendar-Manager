import { Inter, Outfit } from "next/font/google";
import "./globals.css";
import "./layout.css";
import { ThemeProvider } from "@/context/ThemeContext";
import { UserProvider } from "@/context/UserContext";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
});

export const metadata = {
  title: "Group Calendar — AI-Powered Shared Scheduling",
  description:
    "A collaborative scheduling platform for friend groups with an AI assistant.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="system" suppressHydrationWarning>
      <body className={`${inter.variable} ${outfit.variable}`}>
        <ThemeProvider>
          <UserProvider>{children}</UserProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
