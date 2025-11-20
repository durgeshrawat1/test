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
