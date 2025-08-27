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
import AWS from 'aws-sdk';
import { PubSub } from 'graphql-subscriptions';
import dotenv from 'dotenv';
import bodyParser from 'body-parser';
import cors from 'cors';
import { fileURLToPath } from 'url';
import { express as playground } from 'graphql-playground-middleware-express';

dotenv.config();

// Fix __dirname in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load GraphQL schema from file
const typeDefs = fs.readFileSync(path.join(__dirname, 'schema.graphql'), 'utf8');

// AWS SDK setup
AWS.config.update({ region: process.env.AWS_REGION || 'us-east-1' });
const ddb = new AWS.DynamoDB.DocumentClient();
const s3 = new AWS.S3();
const TABLE = process.env.DDB_TABLE || 'YourDynamoDBTable';

// PubSub for subscriptions (in-memory)
const pubsub = new PubSub();
const CREATED = 'DOC_CREATED';
const UPDATED = 'DOC_UPDATED';

// Resolvers
const resolvers = {
  Query: {
    getDocument: async (_, { ObjectKey }) => {
      const res = await ddb.get({
        TableName: TABLE,
        Key: { PK: ObjectKey, SK: ObjectKey }
      }).promise();
      return res.Item || null;
    },

    listDocuments: async () => {
      const res = await ddb.scan({
        TableName: TABLE,
        Limit: 100
      }).promise();
      return { Documents: res.Items || [], nextToken: null };
    },

    getFileContents: async (_, { s3Uri }) => {
      const uriParts = s3Uri.replace('s3://', '').split('/');
      const Bucket = uriParts.shift();
      const Key = uriParts.join('/');
      const res = await s3.getObject({ Bucket, Key }).promise();

      return {
        content: res.Body.toString('utf-8'),
        contentType: res.ContentType,
        size: res.ContentLength,
        isBinary: false
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
      if (!key) throw new Error('ObjectKey is required');

      let updateExpr = 'set';
      const names = {}, values = {};

      for (const [k, v] of Object.entries(input)) {
        if (k === 'ObjectKey') continue;
        updateExpr += ` #${k} = :${k},`;
        names[`#${k}`] = k;
        values[`:${k}`] = v;
      }

      updateExpr = updateExpr.slice(0, -1); // remove trailing comma

      const res = await ddb.update({
        TableName: TABLE,
        Key: { PK: key, SK: key },
        UpdateExpression: updateExpr,
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
            [TABLE]: chunk.map(key => ({
              DeleteRequest: {
                Key: { PK: key, SK: key }
              }
            }))
          }
        }).promise();
      }

      return true;
    }
  },

  Subscription: {
    onCreateDocument: {
      subscribe: () => pubsub.asyncIterator(CREATED)
    },
    onUpdateDocument: {
      subscribe: () => pubsub.asyncIterator(UPDATED)
    }
  }
};

// Build GraphQL schema
const schema = makeExecutableSchema({ typeDefs, resolvers });

// Start Apollo Server with WebSocket support and Playground
async function start() {
  const app = express();
  const httpServer = createServer(app);

  // WebSocket server for subscriptions
  const wsServer = new WebSocketServer({
    server: httpServer,
    path: '/graphql'
  });

  const serverCleanup = useServer({ schema }, wsServer);

  const apollo = new ApolloServer({
    schema,
    plugins: [
      ApolloServerPluginDrainHttpServer({ httpServer }),
      {
        async serverWillStart() {
          return {
            async drainServer() {
              await serverCleanup.dispose();
            }
          };
        }
      }
    ]
  });

  await apollo.start();

  // Serve Playground on GET
  app.get('/graphql', playground({ endpoint: '/graphql' }));

  // GraphQL API on POST
  app.use('/graphql', cors(), bodyParser.json(), expressMiddleware(apollo));

  const port = process.env.PORT || 4000;
  httpServer.listen(port, () => {
    console.log(`🚀 GraphQL ready at http://localhost:${port}/graphql`);
    console.log(`📡 Subscriptions ready at ws://localhost:${port}/graphql`);
  });
}

start();
