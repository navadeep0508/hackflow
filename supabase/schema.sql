-- Update the messages table to include a recipient_id
ALTER TABLE messages
ADD COLUMN recipient_id UUID;

CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_name TEXT NOT NULL,
    description TEXT,
    open_slots INTEGER DEFAULT 0
);

-- Insert some sample data
INSERT INTO teams (team_name, description, open_slots) VALUES
('AI Wizards', 'Building AI solutions for a better world.', 2),
('Code Ninjas', 'Coding our way to success.', 1),
('Data Dreamers', 'Turning data into insights.', 3);

CREATE TABLE team_applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    team_id UUID REFERENCES teams(id),
    application_date TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    status TEXT DEFAULT 'pending' -- e.g., pending, approved, rejected
);

CREATE TABLE user_recruitments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    description TEXT,
    skills TEXT,  -- Comma-separated list of skills
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
); 