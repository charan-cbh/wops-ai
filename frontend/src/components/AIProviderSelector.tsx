import { Fragment } from 'react';
import { Listbox, Transition } from '@headlessui/react';
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/react/20/solid';
import { clsx } from 'clsx';

interface AIProvider {
  name: string;
  available_models: string[];
}

interface AIProviderSelectorProps {
  providers: Record<string, AIProvider>;
  selectedProvider: string;
  selectedModel: string;
  onProviderChange: (provider: string, model: string) => void;
}

export default function AIProviderSelector({
  providers,
  selectedProvider,
  selectedModel,
  onProviderChange,
}: AIProviderSelectorProps) {
  const providerOptions = Object.entries(providers).map(([key, provider]) => ({
    id: key,
    name: provider.name,
    models: provider.available_models,
  }));

  const currentProvider = providerOptions.find(p => p.id === selectedProvider);
  const availableModels = currentProvider?.models || [];

  const handleProviderChange = (providerId: string) => {
    const provider = providerOptions.find(p => p.id === providerId);
    if (provider && provider.models.length > 0) {
      onProviderChange(providerId, provider.models[0]);
    }
  };

  const handleModelChange = (model: string) => {
    onProviderChange(selectedProvider, model);
  };

  return (
    <div className="flex items-center space-x-4">
      <div className="flex-1">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          AI Provider
        </label>
        <Listbox value={selectedProvider} onChange={handleProviderChange}>
          <div className="relative">
            <Listbox.Button className="relative w-full cursor-default rounded-lg bg-white py-2 pl-3 pr-10 text-left border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent sm:text-sm">
              <span className="block truncate">{currentProvider?.name || 'Select Provider'}</span>
              <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                <ChevronUpDownIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
              </span>
            </Listbox.Button>
            <Transition
              as={Fragment}
              leave="transition ease-in duration-100"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <Listbox.Options className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                {providerOptions.map((provider) => (
                  <Listbox.Option
                    key={provider.id}
                    className={({ active }) =>
                      clsx(
                        'relative cursor-default select-none py-2 pl-10 pr-4',
                        active ? 'bg-blue-100 text-blue-900' : 'text-gray-900'
                      )
                    }
                    value={provider.id}
                  >
                    {({ selected }) => (
                      <>
                        <span className={clsx('block truncate', selected ? 'font-medium' : 'font-normal')}>
                          {provider.name}
                        </span>
                        {selected ? (
                          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-blue-600">
                            <CheckIcon className="h-5 w-5" aria-hidden="true" />
                          </span>
                        ) : null}
                      </>
                    )}
                  </Listbox.Option>
                ))}
              </Listbox.Options>
            </Transition>
          </div>
        </Listbox>
      </div>

      <div className="flex-1">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Model
        </label>
        <Listbox value={selectedModel} onChange={handleModelChange}>
          <div className="relative">
            <Listbox.Button className="relative w-full cursor-default rounded-lg bg-white py-2 pl-3 pr-10 text-left border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent sm:text-sm">
              <span className="block truncate">{selectedModel || 'Select Model'}</span>
              <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                <ChevronUpDownIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
              </span>
            </Listbox.Button>
            <Transition
              as={Fragment}
              leave="transition ease-in duration-100"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <Listbox.Options className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                {availableModels.map((model) => (
                  <Listbox.Option
                    key={model}
                    className={({ active }) =>
                      clsx(
                        'relative cursor-default select-none py-2 pl-10 pr-4',
                        active ? 'bg-blue-100 text-blue-900' : 'text-gray-900'
                      )
                    }
                    value={model}
                  >
                    {({ selected }) => (
                      <>
                        <span className={clsx('block truncate', selected ? 'font-medium' : 'font-normal')}>
                          {model}
                        </span>
                        {selected ? (
                          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-blue-600">
                            <CheckIcon className="h-5 w-5" aria-hidden="true" />
                          </span>
                        ) : null}
                      </>
                    )}
                  </Listbox.Option>
                ))}
              </Listbox.Options>
            </Transition>
          </div>
        </Listbox>
      </div>
    </div>
  );
}