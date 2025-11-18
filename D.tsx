import type { NextApiRequest, NextApiResponse } from "next";
import { jwtVerify, createRemoteJWKSet } from "jose";

// Cognito JWKS URL
const JWKS_URL = `https://cognito-idp.${process.env.AWS_REGION}.amazonaws.com/${process.env.COGNITO_USER_POOL_ID}/.well-known/jwks.json`;

// Fetch JWKS for verification
const JWKS = createRemoteJWKSet(new URL(JWKS_URL));

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    // 1. Read ALB JWT header
    const albToken = req.headers["x-amzn-oidc-data"] as string | undefined;
    if (!albToken) {
      return res.status(401).json({ error: "No ALB JWT found" });
    }

    // 2. Verify the JWT
    const { payload } = await jwtVerify(albToken, JWKS, {
      issuer: `https://cognito-idp.${process.env.AWS_REGION}.amazonaws.com/${process.env.COGNITO_USER_POOL_ID}`,
    });

    // 3. Extract user info
    const username = payload["cognito:username"] || payload["email"] || payload["sub"];

    // 4. Return user info or token claims to frontend
    // You can also mint a Cognito token via Lambda here if needed
    return res.status(200).json({
      username,
      claims: payload,
      idToken: albToken, // frontend can use this JWT directly
    });

  } catch (err: any) {
    console.error("JWT verification error:", err);
    return res.status(401).json({ error: "Invalid ALB JWT" });
  }
}
