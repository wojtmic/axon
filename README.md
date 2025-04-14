# Axon
## WARNING: Axon is in an early BETA state! Some features may not be complete, stuff may not look good, etc.
Axon is a hyper-configurable launcher like [Rofi](https://github.com/davatorium/rofi) or [Sherlock](https://github.com/Skxxtz/sherlock).

# Configuration
Nothing in Axon is hardcoded. For refrence, the default config:
```jsonc
{
    "placeholder": "Search...",
    "entries": [
        {
            "name": "$(playerctl metadata title)", // $() will run a command, like in Bash
            "action": {"run": "playerctl play-pause"}, // The run action runs a Bash command
            "icon": "$(playerctl metadata mpris:artUrl)", // This requires a URL path (tip: use file:// for local)
            "condition": "pgrep spotify" // Condition will run only if the command it runs finishes with a 0 escape code
        },
        {"autogen": "desktop_apps"}, // Autogen will populate the list with autogenerated entries
        { // Allows you to do math!
            "name": "%% = +(%%)", // +() will evaluate a math expression, %% gets replaced with input
            "action": {"copy": "+(%%)"}, // Copy of course copies to the clipboard (with wl-copy, if you wanna do anything else do a RUN)
            "icon": "text://", // The text:// protocol just uses a string to render as an image
            "flags": ["NOTEMPTY"] // Flags add special behavior to an entry. Usually you wont need them, but they may make your config 500% better!
        },
        { // For running commands
            "name": "Run %%",
            "action": {"run": "%%"},
            "icon": "text://",
            "flags": ["NOTEMPTY"]
        }
    ]
}
```

Everything can be customised. Refer to the wiki for more information.

# Instalation
Axon can be and is recommended to be installed from the AUR under the name `axon-applauncher`.

# Contribution
Axon is licensed under GPL-3.0. Feel free to open a pull request!