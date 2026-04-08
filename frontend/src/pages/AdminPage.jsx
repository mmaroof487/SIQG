import React from 'react';
import AdminDashboard from '../components/AdminDashboard';

const AdminPage = ({ token }) => {
  // Check if user is admin (would validate token in real app)
  return (
    <div>
      <AdminDashboard token={token} />
    </div>
  );
};

export default AdminPage;
