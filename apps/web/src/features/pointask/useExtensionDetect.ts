import { useEffect, useState } from 'react';

/** Version string the Point & Ask browser extension writes to <html data-point-ask-extension>, or null when absent. */
export function useExtensionDetect(): string | null {
  const [version, setVersion] = useState<string | null>(() => document.documentElement.dataset.pointAskExtension || null);
  useEffect(() => {
    setVersion(document.documentElement.dataset.pointAskExtension || null);
    const observer = new MutationObserver(() => setVersion(document.documentElement.dataset.pointAskExtension || null));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-point-ask-extension'] });
    return () => observer.disconnect();
  }, []);
  return version;
}
