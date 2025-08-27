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

dotenv.config();

// Load cleaned schema
const typeDefs = fs.readFileSync(path.join(__dirname, 'schema_clean.graphql'), 'utf8');

// AWS SDK config
AWS.config.update({ region: process.env.AWS_REGION || 'us-east-1' });
const ddb = new AWS.DynamoDB.DocumentClient();
const S3 = new AWS.S3();
const TABLE = process.env.DDB_TABLE || 'YourDynamoDBTable';

// PubSub
const pubsub = new PubSub();
const CREATED = 'DOC_CREATED';
const UPDATED = 'DOC_UPDATED';

const schema = makeExecutableSchema({ typeDefs, resolvers: {} });

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
      // Placeholder: parse bucket/key from s3Uri
      const res = await S3.getObject({ Bucket: 'my-bucket', Key: 'path/to/file' }).promise();
      return {
        content: res.Body.toString('utf-8'),
        contentType: res.ContentType,
        size: res.ContentLength,
        isBinary: false,
      };
    },
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
      const attrNames = {}, attrValues = {};
      for (const [k, v] of Object.entries(input)) {
        if (k === 'ObjectKey') continue;
        expr += ` #${k} = :${k},`;
        attrNames[`#${k}`] = k;
        attrValues[`:${k}`] = v;
      }
      expr = expr.slice(0, -1);

      const res = await ddb.update({
        TableName: TABLE,
        Key: { PK: key, SK: key },
        UpdateExpression: expr,
        ExpressionAttributeNames: attrNames,
        ExpressionAttributeValues: attrValues,
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
            [TABLE]: chunk.map(k => ({ DeleteRequest: { Key: { PK: k, SK: k } }}))
          }
        }).promise();
      }
      return true;
    },
  },
  Subscription: {
    onCreateDocument: { subscribe: () => pubsub.asyncIterator(CREATED) },
    onUpdateDocument: { subscribe: () => pubsub.asyncIterator(UPDATED) },
  }
};

schema._resolvers = resolvers; // Attach resolvers to schema

async function start() {
  const app = express();
  const httpServer = createServer(app);

  // Setup WebSocket server for subscriptions
  const wsServer = new WebSocketServer({ server: httpServer, path: '/graphql' });
  const serverCleanup = useServer({ schema }, wsServer);

  const apollo = new ApolloServer({
    schema,
    plugins: [
      ApolloServerPluginDrainHttpServer({ httpServer }),
      {
        async serverWillStart() {
          return { async drainServer() { await serverCleanup.dispose(); } };
        }
      }
    ],
  });

  await apollo.start();
  app.use('/graphql', cors(), bodyParser.json(), expressMiddleware(apollo));

  const port = process.env.PORT || 4000;
  httpServer.listen(port, () => {
    console.log(`GraphQL endpoint: http://localhost:${port}/graphql`);
    console.log(`Subscriptions via ws://localhost:${port}/graphql`);
  });
}

start();
