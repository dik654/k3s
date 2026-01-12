import { useState } from 'react';
import { Key, Database, Bot, Palette, Save, Loader2 } from 'lucide-react';
import clsx from 'clsx';

const tabs = [
  { id: 'credentials', label: 'API Credentials', icon: Key },
  { id: 'vectorstores', label: 'Vector Stores', icon: Database },
  { id: 'models', label: 'AI Models', icon: Bot },
  { id: 'appearance', label: 'Appearance', icon: Palette },
];

export function Settings() {
  const [activeTab, setActiveTab] = useState('credentials');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
  };

  return (
    <div className="flex-1 flex flex-col">
      {/* Header */}
      <div className="h-14 bg-dark-800 border-b border-dark-700 flex items-center justify-between px-6">
        <h1 className="text-lg font-semibold text-white">Settings</h1>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
            'bg-primary-600 text-white hover:bg-primary-700',
            isSaving && 'opacity-50 cursor-not-allowed'
          )}
        >
          {isSaving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          Save Changes
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-56 bg-dark-800 border-r border-dark-700 p-4">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors',
                    activeTab === tab.id
                      ? 'bg-dark-700 text-white'
                      : 'text-dark-400 hover:text-white hover:bg-dark-700'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Settings Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'credentials' && <CredentialsSettings />}
          {activeTab === 'vectorstores' && <VectorStoreSettings />}
          {activeTab === 'models' && <ModelsSettings />}
          {activeTab === 'appearance' && <AppearanceSettings />}
        </div>
      </div>
    </div>
  );
}

function CredentialsSettings() {
  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-medium text-white">API Credentials</h2>
        <p className="text-sm text-dark-400 mt-1">
          Configure your API keys for LLM providers and other services.
        </p>
      </div>

      <div className="space-y-4">
        <CredentialInput
          label="OpenAI API Key"
          placeholder="sk-..."
          description="Required for GPT models and embeddings"
        />
        <CredentialInput
          label="Anthropic API Key"
          placeholder="sk-ant-..."
          description="Required for Claude models"
        />
        <CredentialInput
          label="Pinecone API Key"
          placeholder="..."
          description="Required for Pinecone vector store"
        />
        <CredentialInput
          label="Cohere API Key"
          placeholder="..."
          description="Required for Cohere embeddings"
        />
      </div>
    </div>
  );
}

function CredentialInput({
  label,
  placeholder,
  description,
}: {
  label: string;
  placeholder: string;
  description: string;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-white mb-1.5">
        {label}
      </label>
      <input
        type="password"
        placeholder={placeholder}
        className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white placeholder-dark-500 focus:outline-none focus:border-primary-500"
      />
      <p className="text-xs text-dark-500 mt-1">{description}</p>
    </div>
  );
}

function VectorStoreSettings() {
  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-medium text-white">Vector Store Configuration</h2>
        <p className="text-sm text-dark-400 mt-1">
          Configure your vector database connections.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-white mb-1.5">
            Default Vector Store
          </label>
          <select className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white focus:outline-none focus:border-primary-500">
            <option value="memory">In-Memory</option>
            <option value="pinecone">Pinecone</option>
            <option value="chroma">Chroma</option>
            <option value="qdrant">Qdrant</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-white mb-1.5">
            Pinecone Environment
          </label>
          <input
            type="text"
            placeholder="us-west1-gcp"
            className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white placeholder-dark-500 focus:outline-none focus:border-primary-500"
          />
        </div>
      </div>
    </div>
  );
}

function ModelsSettings() {
  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-medium text-white">AI Models</h2>
        <p className="text-sm text-dark-400 mt-1">
          Configure default models and parameters.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-white mb-1.5">
            Default LLM Provider
          </label>
          <select className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white focus:outline-none focus:border-primary-500">
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="google">Google</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-white mb-1.5">
            Default Model
          </label>
          <select className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white focus:outline-none focus:border-primary-500">
            <option value="gpt-4">GPT-4</option>
            <option value="gpt-4-turbo">GPT-4 Turbo</option>
            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-white mb-1.5">
            Default Temperature
          </label>
          <input
            type="number"
            defaultValue={0.7}
            min={0}
            max={2}
            step={0.1}
            className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white focus:outline-none focus:border-primary-500"
          />
        </div>
      </div>
    </div>
  );
}

function AppearanceSettings() {
  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-medium text-white">Appearance</h2>
        <p className="text-sm text-dark-400 mt-1">
          Customize the look and feel of the application.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-white mb-1.5">
            Theme
          </label>
          <select className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white focus:outline-none focus:border-primary-500">
            <option value="dark">Dark</option>
            <option value="light">Light</option>
            <option value="system">System</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-white mb-1.5">
            Canvas Grid
          </label>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              defaultChecked
              className="w-4 h-4 rounded border-dark-600 bg-dark-700 text-primary-500 focus:ring-primary-500"
            />
            <span className="text-sm text-dark-300">Show grid on canvas</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-white mb-1.5">
            Minimap
          </label>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              defaultChecked
              className="w-4 h-4 rounded border-dark-600 bg-dark-700 text-primary-500 focus:ring-primary-500"
            />
            <span className="text-sm text-dark-300">Show minimap</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Settings;
