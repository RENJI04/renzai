export type Membership = { organization_id: string; membership_id: string; role: string };

export type Session = {
  user: { user_id: string; email: string; status: string; email_verified: boolean };
  csrf_token: string;
  memberships: Membership[];
};

export type Organization = {
  organization_id: string;
  membership_id: string;
  name: string;
  slug: string;
  role: string;
};

export type Member = { membership_id: string; email: string; role: string; status: string };
