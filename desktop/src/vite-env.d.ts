interface InterviewTrainerBridge {
  backendBaseUrl: string;
  platform: string;
  setAlwaysOnTop: (value: boolean) => Promise<boolean>;
}

interface Window {
  interviewTrainer?: InterviewTrainerBridge;
}
