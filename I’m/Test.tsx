import { useSession, signOut } from "next-auth/react";

export default function Home() {
  const { data: session } = useSession();

  if (!session) {
    return (
      <div style={{ textAlign: "center", marginTop: 50 }}>
        <h2>You are not logged in</h2>
        <a href="/login">Go to Login</a>
      </div>
    );
  }

  return (
    <div style={{ textAlign: "center", marginTop: 50 }}>
      <h1>Welcome, {session.user?.name}</h1>
      {session.user?.image && (
        <img
          src={session.user.image}
          alt="Profile"
          style={{ width: 150, height: 150, borderRadius: "50%" }}
        />
      )}
      <div style={{ marginTop: 20 }}>
        <button onClick={() => signOut()}>Logout</button>
      </div>
    </div>
  );
}


import NextAuth from "next-auth";
import CognitoProvider from "next-auth/providers/cognito";

export default NextAuth({
  providers: [
    CognitoProvider({
      clientId: process.env.COGNITO_CLIENT_ID!,
      clientSecret: process.env.COGNITO_CLIENT_SECRET!,
      issuer: process.env.COGNITO_ISSUER_URL!,
      authorization: { params: { scope: "openid profile email" } },
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET!,
  callbacks: {
    async jwt({ token, user, account }) {
      // Persist user info in token
      if (user) {
        token.name = user.name;
        token.email = user.email;
        token.picture = user.image;
      }
      return token;
    },
    async session({ session, token }) {
      // Expose user info to client
      session.user = {
        name: token.name,
        email: token.email,
        image: token.picture,
      };
      return session;
    },
  },
});


NEXTAUTH_URL=https://<ALB-DNS>
NEXTAUTH_SECRET=<a-random-secret-string>

COGNITO_CLIENT_ID=<your-cognito-app-client-id>
COGNITO_CLIENT_SECRET=<your-cognito-app-client-secret>
COGNITO_ISSUER_URL=https://<your-cognito-domain> # e.g., https://your-domain.auth.<region>.amazoncognito.com



  npx create-next-app nextjs-cognito-app
cd nextjs-cognito-app

npm install next-auth @next-auth/cognito-adapter

  
