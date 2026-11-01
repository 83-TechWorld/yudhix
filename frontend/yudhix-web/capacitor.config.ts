import type { CapacitorConfig } from '@capacitor/cli';

// Native shells for the App Store / Play Store wrap the same Angular build.
// Before a store build, set apiUrl in src/environments/environment.prod.ts to your public API.
const config: CapacitorConfig = {
  appId: 'io.yudhix.app',
  appName: 'Yudhix',
  webDir: 'dist/yudhix-web/browser',
  plugins: {
    SplashScreen: { launchShowDuration: 600, backgroundColor: '#4338ca', showSpinner: false },
  },
};

export default config;
