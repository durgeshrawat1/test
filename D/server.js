const { ApolloServer, gql } = require('apollo-server');
const fs = require('fs');
const AWS = require('aws-sdk');

// Config AWS SDK (set your region here)
AWS.config.update({ region: 'your-aws-region' });

const dynamoDb = new AWS.DynamoDB.DocumentClient();
const TABLE_NAME = 'YourDynamoDBTableName';

// Read your full schema.graphql file
const typeDefs = gql`${fs.readFileSync('schema.graphql', 'utf8')}`;

// Helper: map input to DynamoDB keys
const getDynamoKeys = (objectKey) => ({
  PK: objectKey,
  SK: objectKey,
});

// Resolvers implementation
const resolvers = {
  Query: {
    getDocument: async (_, { ObjectKey }) => {
      try {
        const params = {
          TableName: TABLE_NAME,
          Key: getDynamoKeys(ObjectKey),
        };
        const result = await dynamoDb.get(params).promise();
        return result.Item || null;
      } catch (err) {
        console.error('getDocument error:', err);
        throw new Error('Error fetching document');
      }
    },

    listDocuments: async () => {
      try {
        // Scan can be inefficient for large tables; consider using Query with indexes
        const params = {
          TableName: TABLE_NAME,
          Limit: 100,
        };
        const result = await dynamoDb.scan(params).promise();
        return {
          Documents: result.Items || [],
          nextToken: null, // implement pagination token if needed
        };
      } catch (err) {
        console.error('listDocuments error:', err);
        throw new Error('Error listing documents');
      }
    },
  },

  Mutation: {
    createDocument: async (_, { input }) => {
      const objectKey = input.ObjectKey || `doc-${Date.now()}`;
      const item = {
        PK: objectKey,
        SK: objectKey,
        ...input,
      };
      try {
        const params = {
          TableName: TABLE_NAME,
          Item: item,
        };
        await dynamoDb.put(params).promise();
        return { ObjectKey: objectKey };
      } catch (err) {
        console.error('createDocument error:', err);
        throw new Error('Error creating document');
      }
    },

    updateDocument: async (_, { input }) => {
      // DynamoDB update expression builder example (simplified)
      const objectKey = input.ObjectKey;
      if (!objectKey) throw new Error('ObjectKey is required for update');

      // Build UpdateExpression and ExpressionAttributeValues dynamically
      let updateExp = 'set';
      const expAttrValues = {};
      const expAttrNames = {};
      let first = true;

      // exclude keys that are PK and SK
      Object.entries(input).forEach(([key, value]) => {
        if (key === 'ObjectKey') return;
        if (!first) updateExp += ', ';
        updateExp += ` #${key} = :${key}`;
        expAttrValues[`:${key}`] = value;
        expAttrNames[`#${key}`] = key;
        first = false;
      });

      const params = {
        TableName: TABLE_NAME,
        Key: getDynamoKeys(objectKey),
        UpdateExpression: updateExp,
        ExpressionAttributeValues: expAttrValues,
        ExpressionAttributeNames: expAttrNames,
        ReturnValues: 'ALL_NEW',
      };

      try {
        const result = await dynamoDb.update(params).promise();
        return result.Attributes;
      } catch (err) {
        console.error('updateDocument error:', err);
        throw new Error('Error updating document');
      }
    },

    deleteDocument: async (_, { objectKeys }) => {
      try {
        // BatchWriteItem can delete multiple items (max 25 at once)
        if (!objectKeys || !Array.isArray(objectKeys)) {
          throw new Error('objectKeys array is required');
        }

        const deleteRequests = objectKeys.map((key) => ({
          DeleteRequest: {
            Key: getDynamoKeys(key),
          },
        }));

        // DynamoDB BatchWrite limit is 25 items
        const chunks = [];
        for (let i = 0; i < deleteRequests.length; i += 25) {
          chunks.push(deleteRequests.slice(i, i + 25));
        }

        for (const chunk of chunks) {
          const params = {
            RequestItems: {
              [TABLE_NAME]: chunk,
            },
          };
          await dynamoDb.batchWrite(params).promise();
        }

        return true;
      } catch (err) {
        console.error('deleteDocument error:', err);
        throw new Error('Error deleting documents');
      }
    },
  },
};

const server = new ApolloServer({
  typeDefs,
  resolvers,
  // Turn off playground auth if you want
  playground: true,
  introspection: true,
});

server.listen({ port: 4000 }).then(({ url }) => {
  console.log(`🚀 Server ready at ${url}`);
});
