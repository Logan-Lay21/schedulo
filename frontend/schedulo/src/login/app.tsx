import { useState } from 'react';

export default function Login() {
    const [name, setName] = useState('');
    const [password, setPassword] = useState('');
    const [loggedIn, setLoggedIn] = useState(false);

    const handleLogin = () => {
        if (name && password) {
            setLoggedIn(true);
        } else {
            alert('Please enter your name and password');
        }
    };

    return (
        <div className="flex flex-col items-center justify-center h-screen bg-gray-100 space-y-4">
            {loggedIn ? (
                <h2 className="text-xl">Welcome, {name}!</h2>
            ) : (
                <>
                    <input
                        type="text"
                        placeholder="Name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="border p-2 rounded w-80"
                    />
                    <input
                        type="password"
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="border p-2 rounded w-80"
                    />
                    <button onClick={handleLogin} className="w-80 bg-blue-500 text-white p-2 rounded">
                        Login
                    </button>
                </>
            )}
        </div>
    );
}
