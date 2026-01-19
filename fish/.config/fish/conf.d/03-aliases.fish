#Custom Aliases
#
alias l="ls -la"
alias vi="nvim"

# Access folder
alias cddot="cd ~/dotfile"
alias vipath="vi ~/script/env_file/Paths_fifimove.yaml"
alias git-today="git branch $(date "+%Y%m%d");git switch $(date "+%Y%m%d")"
alias git-adhoc="git branch -d feature/CORE-0000; git branch feature/CORE-0000; git switch feature/CORE-0000"
alias jump-mcp="ssh -L 3306:10.199.0.2:3306 lai2301@35.207.124.21"
alias code="cursor"
