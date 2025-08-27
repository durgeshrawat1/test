import express from 'express';
import { createServer } from 'http';
import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';
import { ApolloServerPluginDrainHttpServer } from '@apollo/server/plugin/drainHttpServer';
import { makeExecutableSchema } from '@graphql-tools/schema';
import { WebSocketServer } from 'ws';
import { useServer } from 'graphql-ws/lib/use/ws';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import AWS from 'aws-sdk';
import aws4 from 'aws4';
import { PubSub } from 'graphql-subscriptions';
import dotenv from 'dotenv';
import cors from 'cors';
import bodyParser from 'body-parser';
import playground from 'graphql-playground-middleware-express';

dotenv.config();

// Setup __dirname for ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load GraphQL schema
const typeDefs = fs.readFileSync(path.join(__dirname, 'schema.graphql'), 'utf8');

// AWS configuration
AWS.config.update({ region: process.env.AWS_REGION || 'us-east-1' });
const ddb = new AWS.DynamoDB.DocumentClient();
const s3 = new AWS.S3();
const TABLE = process.env.DDB_TABLE || 'YourDynamoDBTable';

// Subscriptions (in-memory)
const pubsub = new PubSub();
const CREATED = 'DOC_CREATED';
const UPDATED = 'DOC_UPDATED';

// GraphQL Resolvers
const resolvers = {
  Query: {
    getDocument: async (_, { ObjectKey }) => {
      const res = await ddb.get({ TableName: TABLE, Key: { PK: ObjectKey, SK: ObjectKey } }).promise();
      return res.Item || null;
    },
    listDocuments: async () => {
      const res = await ddb.scan({ TableName: TABLE, Limit: 100 }).promise();
      return { Documents: res.Items || [], nextToken: null };
    },
    getFileContents: async (_, { s3Uri }) => {
      const parts = s3Uri.replace('s3://', '').split('/');
      const Bucket = parts.shift();
      const Key = parts.join('/');
      const res = await s3.getObject({ Bucket, Key }).promise();
      return {
        content: res.Body.toString('utf-8'),
        contentType: res.ContentType,
        size: res.ContentLength,
        isBinary: false,
      };
    }
  },
  Mutation: {
    createDocument: async (_, { input }) => {
      const key = input.ObjectKey || `doc-${Date.now()}`;
      const item = { PK: key, SK: key, ...input };
      await ddb.put({ TableName: TABLE, Item: item }).promise();
      pubsub.publish(CREATED, { onCreateDocument: { ObjectKey: key } });
      return { ObjectKey: key };
    },
    updateDocument: async (_, { input }) => {
      const key = input.ObjectKey;
      if (!key) throw new Error('ObjectKey required');
      let expr = 'set';
      const names = {}, values = {};
      for (const [k, v] of Object.entries(input)) {
        if (k === 'ObjectKey') continue;
        expr += ` #${k} = :${k},`;
        names[`#${k}`] = k;
        values[`:${k}`] = v;
      }
      expr = expr.slice(0, -1);
      const res = await ddb.update({
        TableName: TABLE,
        Key: { PK: key, SK: key },
        UpdateExpression: expr,
        ExpressionAttributeNames: names,
        ExpressionAttributeValues: values,
        ReturnValues: 'ALL_NEW'
      }).promise();
      pubsub.publish(UPDATED, { onUpdateDocument: res.Attributes });
      return res.Attributes;
    },
    deleteDocument: async (_, { objectKeys }) => {
      const chunks = [];
      for (let i = 0; i < objectKeys.length; i += 25) {
        chunks.push(objectKeys.slice(i, i + 25));
      }
      for (const chunk of chunks) {
        await ddb.batchWrite({
          RequestItems: {
            [TABLE]: chunk.map(k => ({ DeleteRequest: { Key: { PK: k, SK: k } } }))
          }
        }).promise();
      }
      return true;
    }
  },
  Subscription: {
    onCreateDocument: { subscribe: () => pubsub.asyncIterator(CREATED) },
    onUpdateDocument: { subscribe: () => pubsub.asyncIterator(UPDATED) }
  }
};

// Build schema
const schema = makeExecutableSchema({ typeDefs, resolvers });

// SigV4 verification middleware for Lambda POST requests
function verifySigV4(req, res, next) {
  const credentials = new AWS.EnvironmentCredentials('AWS');
  const { method, originalUrl: path, headers, body } = req;

  const opts = {
    host: req.headers.host,
    path,
    method,
    headers: { ...headers },
    body: JSON.stringify(body)
  };

  try {
    const signed = aws4.sign(opts, credentials);
    const incomingSig = headers.authorization;
    const expectedSig = signed.headers.Authorization;

    if (!incomingSig || incomingSig !== expectedSig) {
      return res.status(403).json({ error: 'Signature verification failed' });
    }
    next();
  } catch (err) {
    return res.status(500).json({ error: 'SigV4 error', details: err.message });
  }
}

// Start Server
async function start() {
  const app = express();
  const httpServer = createServer(app);

  // WebSocket for subscriptions
  const wsServer = new WebSocketServer({ server: httpServer, path: '/graphql' });
  const serverCleanup = useServer({ schema }, wsServer);

  // Apollo Server
  const apollo = new ApolloServer({
    schema,
    introspection: true,
    plugins: [
      ApolloServerPluginDrainHttpServer({ httpServer }),
      {
        async serverWillStart() {
          return { async drainServer() { await serverCleanup.dispose(); } };
        }
      }
    ]
  });

  await apollo.start();

  // Middlewares
  app.use(cors());
  app.use(bodyParser.json());

  // Only validate SigV4 for POSTs to /graphql
  app.use('/graphql', (req, res, next) => {
    if (req.method === 'POST') {
      verifySigV4(req, res, next);
    } else {
      next();
    }
  });

  app.use('/graphql', expressMiddleware(apollo));

  // Serve GraphQL Playground UI
  app.get('/playground', playground({ endpoint: '/graphql' }));

  const port = process.env.PORT || 4000;
  httpServer.listen(port, () => {
    console.log(`🚀 GraphQL API: http://localhost:${port}/graphql`);
    console.log(`📡 Subscriptions: ws://localhost:${port}/graphql`);
    console.log(`🧪 Playground UI: http://localhost:${port}/playground`);
  });
}

start();
