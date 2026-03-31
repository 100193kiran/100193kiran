import type { Meta, StoryObj } from '@storybook/react';
import { Button } from '../src/Button';

const meta: Meta<typeof Button> = {
  title: 'Design System/Button',
  component: Button,
  parameters: { layout: 'centered' }
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = {
  args: { children: 'Primary Button', variant: 'primary' }
};

export const Secondary: Story = {
  args: { children: 'Secondary Button', variant: 'secondary' }
};
