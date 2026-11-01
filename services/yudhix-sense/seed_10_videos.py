import uuid
import psycopg2
from app.db import get_db_connection, DEFAULT_TENANT_ID, DEFAULT_PRODUCT_ID

def seed_10_batch_videos():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM product WHERE tenant_id = %s LIMIT 1;", (DEFAULT_TENANT_ID,))
    p_row = cur.fetchone()
    product_id = p_row[0] if p_row else DEFAULT_PRODUCT_ID

    cur.execute("SELECT id FROM product_knowledge WHERE tenant_id = %s LIMIT 1;", (DEFAULT_TENANT_ID,))
    pk_row = cur.fetchone()
    default_pk_id = pk_row[0] if pk_row else None

    # Define the 7 additional videos to complete the batch of 10
    additional_videos = [
        {
            "video_id": "q10_gT7X8wE",
            "channel_title": "IGN",
            "video_title": "PS5 Pro Hands-On: Is the $700 Upgrade Actually Worth It?",
            "video_url": "https://www.youtube.com/watch?v=q10_gT7X8wE",
            "published_date": "October 2026",
            "duration_seconds": 840,
            "rage_bait_score": 0.15,
            "factual_accuracy_score": 0.92,
            "sensationalism_grade": "FACTUAL_AND_BALANCED",
            "total_claims": 3,
            "misleading_claims_count": 0,
            "summary": "Detailed hands-on evaluation of PS5 Pro enhanced mode, 60fps fidelity modes, and price-to-performance ratio.",
            "claims": [
                {
                    "timestamp_start": "01:30",
                    "timestamp_seconds": 90,
                    "creator_quote": "PS5 Pro supports Wi-Fi 7 (IEEE 802.11be) for lower latency wireless downloads.",
                    "topic": "Wi-Fi 7 Wireless Standard",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.96,
                    "fact_check_analysis": "Confirmed by Sony official hardware connectivity spec sheet.",
                    "official_citation": "PlayStation 5 Pro Hardware Specification §4.2",
                    "incited_comments_count": 78,
                    "sentiment_impact": "POSITIVE"
                },
                {
                    "timestamp_start": "04:15",
                    "timestamp_seconds": 255,
                    "creator_quote": "Over 50 games have official PS5 Pro Enhanced patches ready for launch day.",
                    "topic": "Launch Patch Availability",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.94,
                    "fact_check_analysis": "Verified against PlayStation Blog official launch lineup announcement.",
                    "official_citation": "PlayStation Blog Official Game Lineup Release §1.0",
                    "incited_comments_count": 120,
                    "sentiment_impact": "POSITIVE"
                },
                {
                    "timestamp_start": "08:50",
                    "timestamp_seconds": 530,
                    "creator_quote": "The vertical stand is sold separately from the console box.",
                    "topic": "Vertical Stand In-Box Inclusions",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.99,
                    "fact_check_analysis": "Accurate packaging specification confirmed across all regions.",
                    "official_citation": "PlayStation Retail Package Bill of Materials",
                    "incited_comments_count": 210,
                    "sentiment_impact": "NEUTRAL"
                }
            ]
        },
        {
            "video_id": "m32_zR9P1kL",
            "channel_title": "Gameranx",
            "video_title": "10 Big PlayStation Decisions That Confused Gamers",
            "video_url": "https://www.youtube.com/watch?v=m32_zR9P1kL",
            "published_date": "September 2026",
            "duration_seconds": 920,
            "rage_bait_score": 0.62,
            "factual_accuracy_score": 0.58,
            "sensationalism_grade": "HIGH_SENSATIONALISM",
            "total_claims": 4,
            "misleading_claims_count": 2,
            "summary": "Retrospective countdown exploring console pricing, disc drive pairing requirements, and PSN PC requirements.",
            "claims": [
                {
                    "timestamp_start": "02:10",
                    "timestamp_seconds": 130,
                    "creator_quote": "Sony secretly removed the optical audio port from the PS5 Pro redesign.",
                    "topic": "Audio Connectivity Ports",
                    "verdict": "MISLEADING",
                    "confidence_score": 0.89,
                    "fact_check_analysis": "The original PS5 never included an optical TOSLINK port; audio has used HDMI eARC since 2020 launch.",
                    "official_citation": "PlayStation Console Architecture Specification §6.1",
                    "incited_comments_count": 310,
                    "sentiment_impact": "NEGATIVE"
                },
                {
                    "timestamp_start": "05:45",
                    "timestamp_seconds": 345,
                    "creator_quote": "Digital game purchases cannot be shared across multiple household consoles.",
                    "topic": "Console Game Sharing Policy",
                    "verdict": "MISLEADING",
                    "confidence_score": 0.95,
                    "fact_check_analysis": "Directly contradicts Sony Console Sharing & Offline Play policy allowing primary console family sharing.",
                    "official_citation": "PlayStation Network Terms of Service §8.4",
                    "incited_comments_count": 520,
                    "sentiment_impact": "NEGATIVE"
                },
                {
                    "timestamp_start": "09:20",
                    "timestamp_seconds": 560,
                    "creator_quote": "The detachable disc drive fits both the PS5 Slim and PS5 Pro models.",
                    "topic": "Disc Drive Universal Compatibility",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.98,
                    "fact_check_analysis": "Verified with PlayStation Direct hardware accessory specifications.",
                    "official_citation": "Sony Hardware Compatibility Matrix",
                    "incited_comments_count": 140,
                    "sentiment_impact": "POSITIVE"
                },
                {
                    "timestamp_start": "12:15",
                    "timestamp_seconds": 735,
                    "creator_quote": "Existing DualSense and DualSense Edge controllers are 100% compatible with PS5 Pro.",
                    "topic": "Controller Backward Compatibility",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.99,
                    "fact_check_analysis": "Confirmed by Sony Interactive Entertainment peripheral guidelines.",
                    "official_citation": "DualSense Hardware Guidelines §2.0",
                    "incited_comments_count": 88,
                    "sentiment_impact": "POSITIVE"
                }
            ]
        },
        {
            "video_id": "b45_wK2L8vM",
            "channel_title": "MKBHD",
            "video_title": "PlayStation 5 Pro Impressions: The Console Price Ceiling",
            "video_url": "https://www.youtube.com/watch?v=b45_wK2L8vM",
            "published_date": "October 2026",
            "duration_seconds": 790,
            "rage_bait_score": 0.35,
            "factual_accuracy_score": 0.88,
            "sensationalism_grade": "FACTUAL_AND_BALANCED",
            "total_claims": 3,
            "misleading_claims_count": 1,
            "summary": "Industrial design review focusing on build quality, fan thermals, 2TB SSD speeds, and market pricing tier.",
            "claims": [
                {
                    "timestamp_start": "02:40",
                    "timestamp_seconds": 160,
                    "creator_quote": "PS5 Pro draws up to 450W power under full synthetic ray tracing loads.",
                    "topic": "Power Supply & Thermal Consumption",
                    "verdict": "MISLEADING",
                    "confidence_score": 0.91,
                    "fact_check_analysis": "Power consumption benchmarks peak at 245W under heavy ray tracing; 450W is the rated PSU ceiling headroom.",
                    "official_citation": "Sony Hardware Thermal & Power Specification §3.1",
                    "incited_comments_count": 285,
                    "sentiment_impact": "NEGATIVE"
                },
                {
                    "timestamp_start": "05:10",
                    "timestamp_seconds": 310,
                    "creator_quote": "The 2TB internal SSD delivers read speeds of roughly 5,500 MB/s uncompressed.",
                    "topic": "NVMe Read Performance",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.97,
                    "fact_check_analysis": "Accurate measurement matching PCIe Gen4 x4 controller specifications.",
                    "official_citation": "PlayStation Storage Architecture Whitepaper",
                    "incited_comments_count": 92,
                    "sentiment_impact": "POSITIVE"
                },
                {
                    "timestamp_start": "09:30",
                    "timestamp_seconds": 570,
                    "creator_quote": "PS5 Pro side plates are sized differently from the standard PS5 Slim plates.",
                    "topic": "Side Plate Cover Swapping",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.99,
                    "fact_check_analysis": "Confirmed by Sony official cover compatibility FAQ.",
                    "official_citation": "Sony Hardware Accessories FAQ §1.2",
                    "incited_comments_count": 165,
                    "sentiment_impact": "NEUTRAL"
                }
            ]
        },
        {
            "video_id": "h78_yP4Q3nB",
            "channel_title": "PlayStation Official",
            "video_title": "PlayStation 5 Pro Technical Presentation hosted by Mark Cerny",
            "video_url": "https://www.youtube.com/watch?v=h78_yP4Q3nB",
            "published_date": "September 2026",
            "duration_seconds": 560,
            "rage_bait_score": 0.05,
            "factual_accuracy_score": 0.99,
            "sensationalism_grade": "FACTUAL_AND_BALANCED",
            "total_claims": 4,
            "misleading_claims_count": 0,
            "summary": "Lead Architect Mark Cerny presents the Big Three pillars of PS5 Pro: upgraded GPU, advanced ray tracing, and PSSR.",
            "claims": [
                {
                    "timestamp_start": "01:10",
                    "timestamp_seconds": 70,
                    "creator_quote": "PS5 Pro features a GPU with 67% more Compute Units than the current PS5 console.",
                    "topic": "GPU Compute Unit Scale",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.99,
                    "fact_check_analysis": "Official primary hardware engineering disclosure by Lead Architect.",
                    "official_citation": "PlayStation 5 Pro Architecture Briefing §1.0",
                    "incited_comments_count": 1420,
                    "sentiment_impact": "POSITIVE"
                },
                {
                    "timestamp_start": "03:40",
                    "timestamp_seconds": 220,
                    "creator_quote": "Memory bandwidth is increased by 28% for faster scene rendering.",
                    "topic": "GDDR6 Bandwidth Upgrade",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.99,
                    "fact_check_analysis": "Verified engineering specification: 576 GB/s bandwidth.",
                    "official_citation": "Sony Hardware Technical Whitepaper §2.1",
                    "incited_comments_count": 680,
                    "sentiment_impact": "POSITIVE"
                },
                {
                    "timestamp_start": "05:55",
                    "timestamp_seconds": 355,
                    "creator_quote": "PlayStation Spectral Super Resolution applies machine learning to boost sharpness and framerates.",
                    "topic": "PSSR AI Neural Reconstruction",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.99,
                    "fact_check_analysis": "Primary announcement of proprietary Sony neural upscaler.",
                    "official_citation": "Sony Interactive Entertainment R&D Documentation",
                    "incited_comments_count": 1940,
                    "sentiment_impact": "POSITIVE"
                },
                {
                    "timestamp_start": "07:20",
                    "timestamp_seconds": 440,
                    "creator_quote": "Game Boost stabilizes and improves performance on over 8,500 backward-compatible PS4 games.",
                    "topic": "PS4 Backward Compatibility Boost",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.98,
                    "fact_check_analysis": "Verified backward compatibility testing coverage.",
                    "official_citation": "PlayStation Backward Compatibility Verification Lab",
                    "incited_comments_count": 810,
                    "sentiment_impact": "POSITIVE"
                }
            ]
        },
        {
            "video_id": "x56_tM8R2pQ",
            "channel_title": "Moore’s Law Is Dead",
            "video_title": "PS5 Pro RDNA 3.5 & Custom Machine Learning Silicon Deep Dive",
            "video_url": "https://www.youtube.com/watch?v=x56_tM8R2pQ",
            "published_date": "October 2026",
            "duration_seconds": 1120,
            "rage_bait_score": 0.44,
            "factual_accuracy_score": 0.76,
            "sensationalism_grade": "MODERATE_SENSATIONALISM",
            "total_claims": 3,
            "misleading_claims_count": 1,
            "summary": "Semiconductor analysis exploring custom TSMC N4P node, cache topology, and FP16 neural tensor throughput.",
            "claims": [
                {
                    "timestamp_start": "03:15",
                    "timestamp_seconds": 195,
                    "creator_quote": "PS5 Pro AI tensor unit delivers approximately 300 TOPS of 8-bit inference compute.",
                    "topic": "Tensor Engine Throughput",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.93,
                    "fact_check_analysis": "Matches Sony internal developer documentation leaked and subsequently confirmed.",
                    "official_citation": "PlayStation Developer Architecture SDK Guide §4.0",
                    "incited_comments_count": 195,
                    "sentiment_impact": "POSITIVE"
                },
                {
                    "timestamp_start": "08:30",
                    "timestamp_seconds": 510,
                    "creator_quote": "The CPU frequency is overclocked to 4.2 GHz using liquid metal thermal paste.",
                    "topic": "CPU Clock Frequency Target",
                    "verdict": "MISLEADING",
                    "confidence_score": 0.94,
                    "fact_check_analysis": "High CPU Frequency Mode caps at 3.85 GHz (a 10% boost over base 3.5 GHz), not 4.2 GHz.",
                    "official_citation": "Sony Hardware Engineering Specification §1.3",
                    "incited_comments_count": 340,
                    "sentiment_impact": "NEGATIVE"
                },
                {
                    "timestamp_start": "13:45",
                    "timestamp_seconds": 825,
                    "creator_quote": "Developers can allocate an extra 1.2 GB of system RAM for game application logic.",
                    "topic": "Developer Memory Budget",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.96,
                    "fact_check_analysis": "OS memory footprint was reduced from 3.5GB to 2.3GB, freeing 1.2GB for games.",
                    "official_citation": "PlayStation SDK OS Memory Allocation Map",
                    "incited_comments_count": 130,
                    "sentiment_impact": "POSITIVE"
                }
            ]
        },
        {
            "video_id": "c91_vK7L4wZ",
            "channel_title": "Eurogamer",
            "video_title": "PSVR2 on PC Tested: Does Sony’s VR Headset Shine on Steam?",
            "video_url": "https://www.youtube.com/watch?v=c91_vK7L4wZ",
            "published_date": "August 2026",
            "duration_seconds": 810,
            "rage_bait_score": 0.10,
            "factual_accuracy_score": 0.96,
            "sensationalism_grade": "FACTUAL_AND_BALANCED",
            "total_claims": 3,
            "misleading_claims_count": 0,
            "summary": "PC adapter hardware testing across Half-Life: Alyx, DisplayPort 1.4 requirements, and SteamVR integration.",
            "claims": [
                {
                    "timestamp_start": "02:00",
                    "timestamp_seconds": 120,
                    "creator_quote": "The official PC adapter allows dual 2000x2040 OLED panels to render SteamVR games.",
                    "topic": "PC Display Resolution Support",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.98,
                    "fact_check_analysis": "Direct match with PlayStation VR2 PC Adapter technical requirements.",
                    "official_citation": "PS VR2 PC Adapter Hardware Requirements §1.0",
                    "incited_comments_count": 110,
                    "sentiment_impact": "POSITIVE"
                },
                {
                    "timestamp_start": "05:25",
                    "timestamp_seconds": 325,
                    "creator_quote": "HDR and eye-tracking foveated rendering are not available when running on PC SteamVR.",
                    "topic": "PC Feature Availability Differences",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.99,
                    "fact_check_analysis": "Explicitly stated in Sony PS VR2 PC Adapter documentation and setup guide.",
                    "official_citation": "PlayStation Blog Official PS VR2 PC Guide §3.0",
                    "incited_comments_count": 240,
                    "sentiment_impact": "NEUTRAL"
                },
                {
                    "timestamp_start": "09:10",
                    "timestamp_seconds": 550,
                    "creator_quote": "Requires a dedicated DisplayPort 1.4 cable and Bluetooth 4.0 adapter.",
                    "topic": "PC Hardware Prerequisites",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.99,
                    "fact_check_analysis": "Accurately cites minimum PC system specifications.",
                    "official_citation": "PlayStation VR2 PC Setup Manual §2.2",
                    "incited_comments_count": 75,
                    "sentiment_impact": "POSITIVE"
                }
            ]
        },
        {
            "video_id": "e12_sP5Q9xT",
            "channel_title": "Dave2D",
            "video_title": "PlayStation Portal - The Weirdest Device I Actually Love",
            "video_url": "https://www.youtube.com/watch?v=e12_sP5Q9xT",
            "published_date": "July 2026",
            "duration_seconds": 650,
            "rage_bait_score": 0.12,
            "factual_accuracy_score": 0.95,
            "sensationalism_grade": "FACTUAL_AND_BALANCED",
            "total_claims": 3,
            "misleading_claims_count": 0,
            "summary": "Handheld ergonomic review, 1080p screen quality, Remote Play bitrates, and home network optimization.",
            "claims": [
                {
                    "timestamp_start": "01:30",
                    "timestamp_seconds": 90,
                    "creator_quote": "PlayStation Portal requires an active PS5 console to stream games locally or over internet.",
                    "topic": "Remote Play Architecture",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.99,
                    "fact_check_analysis": "Verified: Portal is a dedicated Remote Play streaming device, not a standalone console.",
                    "official_citation": "PlayStation Portal System Manual §1.1",
                    "incited_comments_count": 180,
                    "sentiment_impact": "POSITIVE"
                },
                {
                    "timestamp_start": "04:10",
                    "timestamp_seconds": 250,
                    "creator_quote": "Minimum recommended broadband speed is 5 Mbps, with 15 Mbps for optimal 1080p 60fps.",
                    "topic": "Bandwidth Network Requirements",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.98,
                    "fact_check_analysis": "Matches PlayStation Portal network bandwidth guidelines exactly.",
                    "official_citation": "PlayStation Support Network Speed Guidelines §2.0",
                    "incited_comments_count": 95,
                    "sentiment_impact": "POSITIVE"
                },
                {
                    "timestamp_start": "06:40",
                    "timestamp_seconds": 400,
                    "creator_quote": "Supports PlayStation Link wireless audio protocol for lossless low-latency Pulse earbuds.",
                    "topic": "PlayStation Link Protocol",
                    "verdict": "FACTUALLY_CORRECT",
                    "confidence_score": 0.99,
                    "fact_check_analysis": "Direct confirmation of built-in PS Link wireless audio hardware.",
                    "official_citation": "PlayStation Link Wireless Audio Whitepaper",
                    "incited_comments_count": 110,
                    "sentiment_impact": "POSITIVE"
                }
            ]
        }
    ]

    for v in additional_videos:
        # Check if already exists
        cur.execute("SELECT id FROM video_truth_analysis WHERE tenant_id = %s AND video_id = %s;", (DEFAULT_TENANT_ID, v["video_id"]))
        existing = cur.fetchone()
        if existing:
            v_id = existing[0]
            print(f"Video {v['video_id']} already exists ({v_id})")
        else:
            v_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO video_truth_analysis (
                    id, tenant_id, video_id, channel_title, video_title, video_url,
                    published_date, duration_seconds, rage_bait_score, factual_accuracy_score,
                    sensationalism_grade, total_claims, misleading_claims_count, summary, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
            """, (
                v_id, DEFAULT_TENANT_ID, v["video_id"], v["channel_title"],
                v["video_title"], v["video_url"], v["published_date"], v["duration_seconds"],
                v["rage_bait_score"], v["factual_accuracy_score"], v["sensationalism_grade"],
                v["total_claims"], v["misleading_claims_count"], v["summary"]
            ))
            print(f"Inserted video {v['video_id']} ({v['channel_title']})")

            for c in v["claims"]:
                c_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO video_claim (
                        id, tenant_id, video_analysis_id, rag_knowledge_id, timestamp_start,
                        timestamp_seconds, creator_quote, topic, verdict, confidence_score,
                        fact_check_analysis, official_citation, incited_comments_count,
                        sentiment_impact, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
                """, (
                    c_id, DEFAULT_TENANT_ID, v_id, default_pk_id, c["timestamp_start"],
                    c["timestamp_seconds"], c["creator_quote"], c["topic"], c["verdict"],
                    c["confidence_score"], c["fact_check_analysis"], c["official_citation"],
                    c["incited_comments_count"], c["sentiment_impact"]
                ))
            print(f"  Inserted {len(v['claims'])} claims for {v['video_id']}")

    conn.commit()

    cur.execute("SELECT count(*) FROM video_truth_analysis WHERE tenant_id = %s;", (DEFAULT_TENANT_ID,))
    total = cur.fetchone()[0]
    print(f"\nSUCCESS! Total videos in database now: {total}")
    conn.close()

if __name__ == "__main__":
    seed_10_batch_videos()
