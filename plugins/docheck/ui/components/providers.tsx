"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Toaster } from "sonner";
import { AuthGuard } from "./AuthGuard";
import { installAuthInterceptor } from "@/lib/auth";
import { IntlProvider } from "./i18n/IntlProvider";
import { useTheme } from "@/lib/theme";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
      }),
  );
  useEffect(() => {
    installAuthInterceptor();
  }, []);
  const { resolvedTheme } = useTheme();
  return (
    <QueryClientProvider client={client}>
      <IntlProvider>
        <AuthGuard>{children}</AuthGuard>
      </IntlProvider>
      <Toaster
        theme={resolvedTheme}
        position="bottom-right"
        toastOptions={{
          style: {
            background: "rgb(var(--bg-panel-elev))",
            border: "1px solid rgb(var(--border))",
            color: "rgb(var(--text-primary))",
          },
        }}
      />
    </QueryClientProvider>
  );
}
