"""
운동인증방 Discord Bot
슬래시 커맨드 기반 운동 인증 시스템
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, time
from typing import Optional
import pytz

from config import (
    DISCORD_BOT_TOKEN,
    DISCORD_GUILD_ID,
    DISCORD_CHANNEL_ID,
    TIMEZONE,
    WEEKLY_REQUIRED_COUNT,
    PENALTY_PER_MISS
)
from sheets import get_sheets_manager

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tz = pytz.timezone(TIMEZONE)


@bot.event
async def on_ready():
    """봇 시작시 실행"""
    print(f"✅ {bot.user} 로그인 완료!")
    print(f"📊 연결된 서버: {len(bot.guilds)}개")
    
    # 슬래시 커맨드 동기화
    try:
        guild = discord.Object(id=DISCORD_GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"🔄 {len(synced)}개 슬래시 커맨드 동기화 완료")
    except Exception as e:
        print(f"❌ 커맨드 동기화 실패: {e}")
    
    # 주간 집계 스케줄러 시작
    if not weekly_summary.is_running():
        weekly_summary.start()


@bot.tree.command(
    name="인증",
    description="운동 인증을 등록합니다. 사진을 첨부해주세요!",
    guild=discord.Object(id=DISCORD_GUILD_ID)
)
@app_commands.describe(
    회차="인증 회차 (1, 2, 3)",
    벌금차감="납부한 벌금 금액 (선택사항)",
    비고="추가 메모 (선택사항)"
)
async def verify_exercise(
    interaction: discord.Interaction,
    회차: app_commands.Range[int, 1, 3],
    벌금차감: Optional[int] = 0,
    비고: Optional[str] = ""
):
    """운동 인증 커맨드"""
    await interaction.response.defer()
    
    user_id = str(interaction.user.id)
    user_name = interaction.user.display_name
    
    # 이미지 첨부 확인 (메시지에서)
    image_url = None
    
    # NOTE: 슬래시 커맨드는 첨부파일을 직접 받을 수 없음
    # 대안: 인증 후 채널에 사진을 올리도록 안내하거나, 
    # 별도의 attachment 파라미터 추가 가능
    
    try:
        sheets = get_sheets_manager()
        
        # 멤버 등록 확인 (없으면 자동 등록)
        sheets.register_member(user_id, user_name)
        
        # 인증 기록
        result = sheets.add_verification(
            user_id=user_id,
            user_name=user_name,
            count=회차,
            image_url=image_url,
            penalty_paid=벌금차감,
            note=비고
        )
        
        if result["success"]:
            # 현재 주 인증 현황
            weekly_count = sheets.get_user_weekly_count(user_id)
            remaining = max(0, WEEKLY_REQUIRED_COUNT - weekly_count)
            
            embed = discord.Embed(
                title="🏋️ 운동 인증 완료!",
                color=discord.Color.green()
            )
            embed.add_field(name="회원", value=user_name, inline=True)
            embed.add_field(name="회차", value=f"{회차}회", inline=True)
            embed.add_field(name="주간 현황", value=f"{weekly_count}/{WEEKLY_REQUIRED_COUNT}회", inline=True)
            
            if remaining > 0:
                embed.add_field(
                    name="남은 횟수", 
                    value=f"{remaining}회 (예상 벌금: {remaining * PENALTY_PER_MISS:,}원)", 
                    inline=False
                )
            else:
                embed.add_field(name="✅", value="이번 주 운동 완료!", inline=False)
            
            if 벌금차감 > 0:
                embed.add_field(name="💰 벌금 납부", value=f"{벌금차감:,}원", inline=True)
            
            if 비고:
                embed.add_field(name="📝 비고", value=비고, inline=False)
            
            embed.set_footer(text=f"인증 시간: {datetime.now(tz).strftime('%Y-%m-%d %H:%M')}")
            
            await interaction.followup.send(embed=embed)
            
            # 사진 첨부 안내
            await interaction.followup.send(
                "📸 **인증 사진을 이 메시지에 답장으로 첨부해주세요!**\n"
                "(타임스탬프 앱 스크린샷 또는 운동 인증 사진)",
                ephemeral=True
            )
        else:
            await interaction.followup.send(result["message"])
            
    except Exception as e:
        await interaction.followup.send(f"❌ 오류가 발생했습니다: {str(e)}")


@bot.tree.command(
    name="벌금조회",
    description="본인의 벌금 현황을 조회합니다.",
    guild=discord.Object(id=DISCORD_GUILD_ID)
)
async def check_penalty(interaction: discord.Interaction):
    """벌금 조회 커맨드"""
    await interaction.response.defer(ephemeral=True)
    
    user_id = str(interaction.user.id)
    
    try:
        sheets = get_sheets_manager()
        result = sheets.get_user_penalty(user_id)
        
        if not result["success"]:
            await interaction.followup.send(
                "❌ 등록되지 않은 멤버입니다. `/인증` 명령어로 먼저 인증해주세요.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="💰 벌금 현황",
            color=discord.Color.gold()
        )
        embed.add_field(name="회원", value=result["user_name"], inline=True)
        embed.add_field(name="누적 벌금", value=f"{result['total_penalty']:,}원", inline=True)
        embed.add_field(
            name="이번 주 인증", 
            value=f"{result['weekly_count']}/{WEEKLY_REQUIRED_COUNT}회", 
            inline=True
        )
        
        if result["remaining"] > 0:
            embed.add_field(
                name="⚠️ 남은 횟수", 
                value=f"{result['remaining']}회", 
                inline=True
            )
            embed.add_field(
                name="예상 추가 벌금", 
                value=f"{result['potential_penalty']:,}원", 
                inline=True
            )
        else:
            embed.add_field(name="✅", value="이번 주 운동 완료!", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"❌ 오류가 발생했습니다: {str(e)}", ephemeral=True)


@bot.tree.command(
    name="주간현황",
    description="전체 멤버의 주간 운동 현황을 확인합니다.",
    guild=discord.Object(id=DISCORD_GUILD_ID)
)
async def weekly_status(interaction: discord.Interaction):
    """주간 현황 커맨드"""
    await interaction.response.defer()
    
    try:
        sheets = get_sheets_manager()
        status_list = sheets.get_weekly_status()
        
        if not status_list:
            await interaction.followup.send("📋 등록된 멤버가 없습니다.")
            return
        
        week_name, week_start, week_end = sheets.get_current_week_info()
        
        embed = discord.Embed(
            title="📊 주간 운동 현황",
            description=f"📅 {week_start.strftime('%m/%d')} ~ {week_end.strftime('%m/%d')}",
            color=discord.Color.blue()
        )
        
        # 완료자 / 미완료자 분리
        completed = [s for s in status_list if s["completed"]]
        incomplete = [s for s in status_list if not s["completed"]]
        
        if completed:
            completed_text = "\n".join([
                f"✅ {s['user_name']}: {s['count']}회" for s in completed
            ])
            embed.add_field(name="🏆 완료", value=completed_text, inline=False)
        
        if incomplete:
            incomplete_text = "\n".join([
                f"⏳ {s['user_name']}: {s['count']}/{WEEKLY_REQUIRED_COUNT}회 (남은 {s['remaining']}회)"
                for s in incomplete
            ])
            embed.add_field(name="📝 진행중", value=incomplete_text, inline=False)
        
        embed.set_footer(text=f"주차: {week_name}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ 오류가 발생했습니다: {str(e)}")


@bot.tree.command(
    name="멤버등록",
    description="운동인증방 멤버로 등록합니다.",
    guild=discord.Object(id=DISCORD_GUILD_ID)
)
async def register_member(interaction: discord.Interaction):
    """멤버 등록 커맨드"""
    await interaction.response.defer(ephemeral=True)
    
    user_id = str(interaction.user.id)
    user_name = interaction.user.display_name
    
    try:
        sheets = get_sheets_manager()
        result = sheets.register_member(user_id, user_name)
        
        await interaction.followup.send(result["message"], ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"❌ 오류가 발생했습니다: {str(e)}", ephemeral=True)


@tasks.loop(time=time(hour=0, minute=0, tzinfo=tz))
async def weekly_summary():
    """매일 00:00에 실행, 일요일에만 주간 결산"""
    now = datetime.now(tz)
    
    # 일요일(weekday=6)에만 실행
    if now.weekday() != 6:
        return
    
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        print(f"❌ 채널을 찾을 수 없습니다: {DISCORD_CHANNEL_ID}")
        return
    
    try:
        sheets = get_sheets_manager()
        penalties = sheets.calculate_weekly_penalties()
        
        if not penalties:
            embed = discord.Embed(
                title="🎉 주간 결산",
                description="모든 멤버가 이번 주 운동을 완료했습니다!",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
            return
        
        # 벌금 적용
        sheets.apply_penalties(penalties)
        
        embed = discord.Embed(
            title="📋 주간 결산 - 벌금 부과",
            description="이번 주 운동 미달성 멤버입니다.",
            color=discord.Color.red()
        )
        
        total_penalty = 0
        penalty_text = ""
        for p in penalties:
            penalty_text += f"• {p['user_name']}: {p['missed_count']}회 미달성 → {p['penalty']:,}원\n"
            total_penalty += p['penalty']
        
        embed.add_field(name="벌금 대상", value=penalty_text, inline=False)
        embed.add_field(name="총 벌금", value=f"{total_penalty:,}원", inline=False)
        embed.add_field(
            name="⏰ 납부 기한", 
            value="벌금 발생일로부터 1주일 이내\n연체시 추가 벌금 5,000원",
            inline=False
        )
        
        await channel.send(embed=embed)
        
        # 개별 멘션
        for p in penalties:
            await channel.send(
                f"<@{p['user_id']}> 님, 이번 주 운동 {p['missed_count']}회 미달성으로 "
                f"벌금 **{p['penalty']:,}원**이 부과되었습니다. 💪"
            )
        
    except Exception as e:
        print(f"❌ 주간 결산 오류: {e}")


@weekly_summary.before_loop
async def before_weekly_summary():
    """스케줄러 시작 전 봇 준비 대기"""
    await bot.wait_until_ready()


def run_bot():
    """봇 실행"""
    if not DISCORD_BOT_TOKEN:
        print("❌ DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
        print("   .env 파일을 확인해주세요.")
        return
    
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    run_bot()
