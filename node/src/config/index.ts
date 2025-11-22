export const config = {
  port: Number(process.env.PORT) || 3001,
  nodeEnv: process.env.NODE_ENV || 'development',
  apiToken: process.env.API_TOKEN || '',
  openaiApiKey: process.env.OPENAI_API_KEY || ''
};


